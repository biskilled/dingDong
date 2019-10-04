# -*- coding: utf-8 -*-
# (c) 2017-2019, Tal Shany <tal.shany@biSkilled.com>
#
# This file is part of dingDong
#
# dingDong is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# dingDong is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with dingDong.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import re
import pymongo
from collections import OrderedDict
import pandas as pd

from dingDong.conn.connGlobalDB import baseGlobalDb
from dingDong.misc.enumsJson    import eConn, eJson, findProp
from dingDong.misc.logger       import p
from dingDong.misc.misc         import uniocdeStr
from dingDong.config            import config

DEFAULTS    = { eJson.jValues.DEFAULT_TYPE: 'string', eJson.jValues.SCHEMA: None,
                eJson.jValues.EMPTY: 'null', eJson.jValues.COLFRAME: ("", ""), eJson.jValues.SP: {}}

DATA_TYPES  = { eConn.dataType.DB_VARCHAR:['string', 'regex', 'array', 'ntext'],
                    eConn.dataType.DB_INT:['int', 'long'],
                    eConn.dataType.DB_FLOAT:['double'],
                    eConn.dataType.DB_DATE:['date','timestamp']
                    }


class mongo (baseGlobalDb):
    def __init__ (self, connPropDict=None, conn=None, connUrl=None, connExtraUrl=None,
                  connName=None,connObj=None,  connFilter=None, connIsTar=None,
                  connIsSrc=None, connIsSql=None,
                  dbName=None, isStrict=True):

        self.dbName = self.setProperties(propKey=eJson.jValues.DB_NAME, propDict=connPropDict, propVal=dbName)
        self.isStrict = isStrict
        self.removeId = False

        baseGlobalDb.__init__(self, connPropDict=connPropDict, conn=conn, connUrl=connUrl, connExtraUrl=connExtraUrl,
                                    connName=connName, connObj=connObj, connFilter=connFilter,
                                    connIsTar=connIsTar, connIsSrc=connIsSrc, connIsSql=connIsSql,
                                    defaults=DEFAULTS, dataType=DATA_TYPES)

        ## MongoDb -> {filter}, {projection}
        self.connSql = None

        def __updateFilter (connO):
            errMsg = "MONGO DB QUERY MUST BE STR(COLLECTION NAME) OR LIST [COLLECTION NAME, <?FILTER>, <?PROJECTION>), NOT VALID VALUE: %s " % (connO)
            if isinstance(connO, (list, tuple)):
                if len(connO) == 0 and isinstance(connO[0], str):
                    if not self.connSql:
                        self.connSql = list(connO)
                        self.connSql.append({})
                    else:
                        self.connSql[0] = connO[0]
                elif len(connO) == 2 and isinstance(connO[0], str) and isinstance(connO[1], dict):
                    if not self.connSql:
                        self.connSql = list(connO)
                    else:
                        self.connSql[0] = connO[0]
                        self.connSql[1] = connO[1]
                elif len(connO) == 3 and isinstance(connO[0], str) and isinstance(connO[1], dict) and isinstance(connO[2], dict):
                        self.connSql = connO
                else:
                    p(errMsg, "e")
            elif isinstance(connO, str):
                if not self.connSql:
                    self.connSql = [connO, {}]
                else:
                    self.connSql[0] = connO
            else:
                p(errMsg, "e")

        if self.connIsSql:
            __updateFilter(self.connObj)
            self.connObj    = self.connSql

        elif self.connObj and len(self.connObj)>0 \
                and ('.sql' not in self.connObj and (not self.sqlFullFile or (self.sqlFullFile and self.sqlFullFile not in self.connObj))):
            self.connSql = [{}]
            self.defaultSchema  = None

            if self.connFilter and len (self.connFilter)>0:
                __updateFilter(self.connFilter)
                self.connObj = self.connSql

    def connect(self):
        connDbName = self.setProperties(propKey=eJson.jValues.DB_NAME, propVal=self.dbName)
        self.connDB = pymongo.MongoClient(self.connUrl)
        if connDbName:
            self.cursor = self.connDB[connDbName]

        p("CONNECTED, MONGODB DB:%s, URL:%s" % (connDbName, self.connUrl), "ii")

    def close(self):
        try:
            if self.connDB:
                self.connDB.close()
            self.connDB = None
            self.cursor = None
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            p("ERROR: file name:"+str(fname)+" line: "+str(exc_tb.tb_lineno)+" massage: "+str(exc_obj), "e")

    def test (self):
        try:
            maxSevSelDelay = 1  # Assume 1ms maximum server selection delay
            client = pymongo.MongoClient(self.connUrl,serverSelectionTimeoutMS=maxSevSelDelay)
            i = client.server_info()
            p("MONGO TEST: INSTALLED VERSION:%s" %str(i['version']) )
        except Exception as e:
            err = "Error connecting MONGODB URL: %s, ERROR: %s\n " % (self.connUrl, str(e))
            p (err,"e")
            #err+= traceback.format_exc()

    def isExists(self, tableName, tableSchema=None):
        tableName = self.setTable(tableName=tableName)

        allCollections = self.cursor.collection_names()

        if allCollections and len(allCollections)>0:
            for coll in allCollections:
                if coll.lower() == tableName.lower():
                    p("MONGODB COLLECTION %s EXISTS" % (tableName), "ii")
                    return coll
        p("MONGODB COLLECTION %s NOT EXISTS" % (tableName), "ii")
        return None

    def create(self, stt=None, objName=None, addIndex=None):
        tableName = self.setTable(tableName=objName)

        if not stt or len(stt) == 0:
            p("TABLE %s NOT MAPPED CORRECLTY " % (self.connObj), "e")
            return

        isNew, isChanged, newHistoryTable = self.cloneObject(newStructure=stt, tableName=tableName)

        if isNew or (isChanged and self.update < 2):
            if not self.isStrict:
                p("MONGODB: USING SCHEMALESS CONFIGURATION, WILL BE UPDATE ON LOADING ...")
                return

            ### loading strict collection
            collectionValidaton = {}
            for col in stt:
                if eJson.jSttValues.ALIACE in stt[col] and stt[col][eJson.jSttValues.ALIACE] and len(
                        stt[col][eJson.jSttValues.ALIACE]) > 0:
                    colName = self.wrapColName(col=stt[col][eJson.jSttValues.ALIACE], remove=True)
                else:
                    colName = self.wrapColName(col=col, remove=True)
                colType = stt[col][eJson.jSttValues.TYPE]
                collectionValidaton[colName] = {'bsonType':colType,'description':'must have %s' %(colType)}

            self.cursor.create_collection(tableName, validator = {'$jsonSchema':{'bsonType': "object",'properties':collectionValidaton}})
            p("MONGODB: %s COLLECTION CREATED, VALIDATION: %s" %(tableName, collectionValidaton))

        # Check for index
        if addIndex and self.update != eJson.jUpdate.NO_UPDATE:
            self.addIndexToTable(tableName, addIndex)

        # uppdate = chane current structure (add, remove, update) and load history data into new structure
        if self.update == eJson.jUpdate.UPDATE:
            if newHistoryTable and len(newHistoryTable) > 0:
                pipeline = [{"$match": {}},{"$out": newHistoryTable}]

    def cloneObject(self, newStructure, tableName, tableSchema=None):
        return baseGlobalDb.cloneObject(self, newStructure=newStructure, tableName=tableName, tableSchema=tableSchema )

    def getStructure(self, tableName=None, tableSchema=None, sqlQuery=None):
        return baseGlobalDb.getStructure(self, tableName=tableName, tableSchema=tableSchema, sqlQuery=sqlQuery)

    """ INTERNAL USED: TABLE STRUCTURE : {ColumnName:{Type:ColumnType, ALIACE: ColumnName} .... } """
    def getDBStructure(self, tableName, tableSchema):
        tableName = self.setTable(tableName=tableName)

        ret = OrderedDict()
        try:
            collection = self.isExists(tableName=tableName, tableSchema=tableSchema)
            if collection:

                cntRows = self.cntRows()
                ## there are rows - will use current strucutre
                if cntRows>0:
                    schemaObj = self.cursor[tableName].find_one()
                    if schemaObj and len(schemaObj) > 0:
                        for col in schemaObj:
                            colName = uniocdeStr(col)
                            colType = type(col)
                            ret[colName] = {eJson.jSttValues.TYPE: colType, eJson.jSttValues.ALIACE: None}
                else:
                    collectionInfo = self.cursor.command({'listCollections': 1, 'filter': {'name': collection}})
                    #collectionInfo = self.cursor.get_collection_infos( filter=[collectionsL[tableName.lower()]] )

                    if 'cursor' in collectionInfo:
                        cursorObj = collectionInfo['cursor']

                        if 'firstBatch' in cursorObj:
                            firstBatch = cursorObj['firstBatch']
                            for batch in firstBatch:
                                if 'options' in batch:
                                    validator = batch['options']['validator']
                                    collectionProperties = validator['$jsonSchema']['properties']

                                    for col in collectionProperties:
                                        colType = collectionProperties[col]['bsonType']
                                        ret[uniocdeStr(col)] = {eJson.jSttValues.TYPE: colType, eJson.jSttValues.ALIACE: None}

        except Exception as e:
            p("MONGODB-> %s ERROR:\n %s " %(tableName, str(e)), "e")

        return ret

    """ INTERNAL USED: Complex or simple QUERY STRUCURE:  {ColumnName:{Type:ColumnType, ALIACE: ColumnName} .... } """
    def getQueryStructure(self, sqlQuery=None):
        return baseGlobalDb.getQueryStructure(self, sqlQuery=sqlQuery)

    """ INTERNAL USED: Add index """
    def addIndexToTable(self, tableName, addIndex, tableSchema=None):
        p("MONGODB ---> NOT IMPLEMENTED !!!!")

    def preLoading(self, tableName=None, tableSchema=None, sqlFilter=None):
        return baseGlobalDb.preLoading(self, tableName=tableName, tableSchema=tableSchema, sqlFilter=sqlFilter)

    """ INTERNAL USED: preLoading method """
    def truncate(self, tableName=None, tableSchema=None):
        tableName = self.setTable(tableName=tableName)
        #self.cursor[tableName].drop()
        self.cursor[tableName].remove({})
        p("TYPE:%s, TRUNCATE TABLE:%s" % (self.conn, self.connObj), "ii")

    """ INTERNAL USED: preLoading method """
    def delete(self, sqlFilter, tableName=None, tableSchema=None):
        tableName = self.setTable(tableName=tableName)
        sqlFilter   = sqlFilter if sqlFilter else self.connFilter
        self.cursor[tableName].remove(sqlFilter)
        p("TYPE:%s, DELETE FROM TABLE:%s, WHERE:%s" % (self.conn, self.connObj, sqlFilter), "ii")

    def extract(self, tar, tarToSrc, batchRows=None, addAsTaret=True):
        batchRows       = batchRows if batchRows else self.batchSize
        srcColumns      = None
        fnOnRowsDic     = {}
        execOnRowsDic   = {}
        tarColumns      = []
        sourceSql       = self.connSql

        dfAllRows = pd.DataFrame(list( self.cursor[self.connObj].find(*sourceSql) ))

        if self.removeId and '_id' in dfAllRows:
            del dfAllRows['_id']

        ## There is Source And Target column mapping
        if tarToSrc and len(tarToSrc) > 0:
            mongoColumns = dfAllRows.columns
            mongoColumnsL = [x.lower() for x in mongoColumns]

            for i, col in enumerate(tarToSrc):
                if eJson.jSttValues.SOURCE in tarToSrc[col] and tarToSrc[col][eJson.jSttValues.SOURCE]:
                    srcColumnName = tarToSrc[col][eJson.jSttValues.SOURCE].lower()
                    if srcColumnName in mongoColumnsL:
                        srcColumns.append(mongoColumnsL[srcColumnName])
                        tarColumns.append(col)
                    else:
                        p("%s: %s, SOURCE COLUMN LISTED IN STT NOT EXISTS IN SOURCE TABLE, IGNORE COLUMN !!!!, OBJECT:\n%s" % (self.conn, tarToSrc[col][eJson.jSttValues.SOURCE], self.connObj), "e")
                        continue

                elif col.lower() in mongoColumnsL:
                    srcColumns.append (mongoColumnsL[col.lower()])
                    tarColumns.append(col)
                else:
                    srcColumns.append(mongoColumnsL[col.lower()])
                    dfAllRows[ mongoColumnsL[col.lower()] ] = ""
                    tarColumns.append(col)

                ### ADD FUNCTION
                if eJson.jSttValues.FUNCTION in tarToSrc[col] and tarToSrc[col][eJson.jSttValues.FUNCTION]:
                    fnc = eval(tarToSrc[col][eJson.jSttValues.FUNCTION])
                    fnOnRowsDic[i] = fnc if isinstance(fnc, (list, tuple)) else [fnc]

                ### ADD EXECUTION FUNCTIONS
                elif eJson.jSttValues.EXECFUNC in tarToSrc[col] and len(
                        tarToSrc[col][eJson.jSttValues.EXECFUNC]) > 0:
                    newExcecFunction = tarToSrc[col][eJson.jSttValues.EXECFUNC]
                    regex = r"(\{.*?\})"
                    matches = re.finditer(regex, tarToSrc[col][eJson.jSttValues.EXECFUNC], re.MULTILINE | re.DOTALL)
                    for matchNum, match in enumerate(matches):
                        for groupNum in range(0, len(match.groups())):
                            colName = match.group(1)
                            if colName and len(colName) > 0:
                                colToReplace = match.group(1).replace("{", "").replace("}", "")
                                colToReplace = self.__isColumnExists(colName=colToReplace, tarToSrc=tarToSrc)
                                if colToReplace:
                                    newExcecFunction = newExcecFunction.replace(colName,"{" + str(colToReplace) + "}")
                    execOnRowsDic[i] = newExcecFunction

        if srcColumns and len(srcColumns)>0:
            dfAllRows = dfAllRows[ srcColumns ].values.tolist()
        else:
            dfAllRows = dfAllRows.values.tolist()

        try:
            totalRows = len(dfAllRows)
            while totalRows>0:
                if batchRows and batchRows>0 and batchRows<totalRows:
                    loadRows = dfAllRows[:batchRows]
                    dfAllRows = dfAllRows[batchRows:]
                    rows = self.dataTransform(data=loadRows, functionDict=fnOnRowsDic, execDict=execOnRowsDic)
                    tar.load(rows=rows, targetColumn=tarColumns)
                    totalRows = len(dfAllRows)
                else:
                    rows = self.dataTransform(data=dfAllRows, functionDict=fnOnRowsDic, execDict=execOnRowsDic)
                    tar.load(rows=rows, targetColumn=tarColumns)
                    totalRows = 0
        except Exception as e:
            p("TYPE:%s, OBJECT:%s ERROR FATCHING DATA" % (self.conn, str(self.connObj)), "e")
            p(str(e), "e")

    def load(self, rows, targetColumn):
        totalRows = len(rows) if rows else 0
        if totalRows == 0:
            p("THERE ARE NO ROWS")
            return
        tableName   = self.connObj
        pre, pos    = self.columnFrame[0], self.columnFrame[1]
        ## Compare existint target strucutre
        tarStrucutre = self.getStructure(tableName=self.connObj, tableSchema=self.defaultSchema, sqlQuery=None)
        tarStrucutreL= {x.replace(pre, "").replace(pos, "").lower(): x for x in tarStrucutre}

        removeCol = {}
        for i, col in enumerate (targetColumn):
            if col.replace(pre, "").replace(pos, "").lower() not in tarStrucutreL:
                removeCol[i] = col

        if len (removeCol)>0:
            for num in removeCol:
                p("COLUMN NUMBER %s, NAME: %s NOT EXISTS IN TARGET TABLE, IGNORE COLUMN" %(num,removeCol[num]), "w")
                targetColumn.remove(removeCol[num])

                for i, r in enumerate (rows):
                    rows[i] = list(r)
                    del rows[i][num]

        for i, row in enumerate (rows):
            rows[i] = dict(zip(targetColumn, row))

        try:
            self.cursor[tableName].insert (rows)
            p('MONGODB LOAD COLLECTON %s, TOTAL ROWS: %s >>>>>> ' % (tableName, str(totalRows)), "ii")

        except Exception as e:
            p(u"TYPE:%s, OBJCT:%s ERROR in cursor.executemany !!!!" % (self.conn, self.connObj), "e")
            sampleRes = ['Null' if not r else "'%s'" % r for r in rows[0]]
            p(u"SAMPLE:%s " % u", ".join(sampleRes), "e")
            p(e, "e")
            if config.LOOP_ON_ERROR:
                iCnt = 0
                tCnt = len(rows)
                errDict = {}
                totalErrorToLooap = int(tCnt * 0.1)
                totalErrorsFound = 0
                p("ROW BY ROW ERROR-> LOADING %s OUT OF %s ROWS " % (str(totalErrorToLooap), str(tCnt)),"e")
                for r in rows:
                    try:
                        iCnt += 1
                        self.cursor[tableName].insert(r)
                    except Exception as e:
                        totalErrorsFound += 1
                        if totalErrorsFound > totalErrorToLooap:
                            break
                        errMsg = str(e).lower()

                        if errMsg not in errDict:
                            errDict[errMsg] = 0
                            ret = ""
                            for col in r[0]:
                                if col is None:
                                    ret += "Null, "
                                else:
                                    ret += "'%s'," % (col)
                            p("ROW BY ROW ERROR->" , "e")
                            p(ret, "e")
                            p(e, "e")
                        else:
                            errDict[errMsg] += 1
                p("ROW BY ROW ERROR-> LOADED %s OUT OF %s ROWS" % (str(totalErrorToLooap), str(tCnt)), "e")
                for err in errDict:
                    p("TOTAL ERRORS: %s, MSG: %s: " % (str(err), str(errDict[err])), "e")

    def execMethod(self, method=None):
        raise NotImplementedError("execMethod need to be implemented")

    def merge(self, mergeTable, mergeKeys=None, sourceTable=None):
        raise NotImplementedError("merge need to be implemented")

    def cntRows(self, objName=None):
        tableName =  self.setTable (tableName=objName)
        return self.cursor[tableName].count()

    ########################################################################################################

    """ INTERNAL USED  """
    def setTable (self, tableName, wrapTable=False):
        tableName   = tableName if tableName else self.connObj
        tableName   = self.wrapColName (tableName, remove=not wrapTable)
        return tableName