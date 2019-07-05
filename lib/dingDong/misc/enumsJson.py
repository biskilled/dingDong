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

from collections import OrderedDict

class eJson (object):

    class jKeys (object):
        #  JSON TYPES Keys
        TARGET      = 't'
        SOURCE      = 's'
        MERGE       = 'm'
        QUERY       = 'q'
        SEQUENCE    = 'seq'
        STT         = 'sttappend'
        STTONLY     = 'stt'
        MAP         = 'map'
        COLUMNS     = 'col'
        PARTITION   = 'par'           # not inplemented
        INC         = 'inc'           # not implemented
        EXEC        = 'exec'
        NONO        = 'internal'

        eDict = {
            TARGET: [TARGET, 'target'],  # Target
            SOURCE: [SOURCE, 'source'],  # Source
            MERGE: [MERGE, 'merge'],
            QUERY: [QUERY, 'query'],
            SEQUENCE: [SEQUENCE, 'sequence'],
            STT: [STT, 'sourcetotarget'],
            STTONLY: [STTONLY, 'only'],
            MAP: [MAP, 'mapping'],
            COLUMNS: [COLUMNS, 'columns'],
            PARTITION: [PARTITION, 'partition'],
            INC: [INC, 'incremental']
        }

    class jValues(object):
        # Internal Json keys {'s':{'conn'}}
        NAME        = 'n'
        TYPE        = 'type'
        CONN        = 'conn'
        OBJ         = 'obj'
        FILTER      = 'filter'
        IS_CHANGE   = 'ischange'
        URL         = 'url'
        URLPARAM    = 'eurl'
        URL_FILE    = 'urlfile'
        DEFAULT_TYPE= 'defaultdatatype'
        SCHEMA      = 'schema'
        EMPTY       = 'empty'
        COLFRAME    = 'colFrame'
        SP          = 'sp'
        IS_SOURCE   = 'src'
        IS_TARGET   = 'tar'
        IS_SQL      = 'sql'
        FOLDER      = 'folder'

        eDict = {
            NAME:       [NAME, 'name'],
            TYPE:       [TYPE],
            OBJ:        [OBJ, 'object'],
            FILTER:     [FILTER, 'filter'],
            IS_CHANGE:  [IS_CHANGE, 'model', 'isCahnged'],
            URL:        [URL],
            URLPARAM:   [URLPARAM, 'extra', 'extraparam'],
            FOLDER:     [FOLDER, 'files']

        }
        DIC   = {   NAME:None,TYPE:None,CONN:None,OBJ:None,
                    FILTER:None,IS_CHANGE:None,URL:None,URLPARAM:None,
                    URL_FILE:None,DEFAULT_TYPE:None,SCHEMA:None,EMPTY:None,COLFRAME:None,SP:None,
                    IS_SOURCE:None,IS_TARGET:None, IS_SQL:False, FOLDER:None}

    class jSttValues(object):
        SOURCE  = 's'
        TYPE    = 't'
        ALIACE  = 'a'
        FUNCTION= 'f'
        EXECFUNC= 'e'
        DIC     = {SOURCE: None, TYPE: None, ALIACE:None}

    # Column Name : {Type:XXXX, Alicae: New Column Name}
    class jStrucure(object):
        TYPE    = 'type'
        ALIACE  = 'alias'
        OBJECT  = 'object'
        DIC     = {TYPE:None, ALIACE:None}

    class jMergeValues(object):
        SOURCE  = 'merge_source'
        TARGET  = 'merge_target'
        MERGE   = 'merge_keys'
        DIC     = {SOURCE:None, TARGET:None, MERGE:None}

    class jFile(object):
        MIN_SIZE        = 'min'
        DEF_COLUMN_PREF = 'defCol'
        DECODING        = 'decoding'
        ENCODING        = 'encoding'
        DELIMITER       = 'delimiter'
        ROW_HEADER      = 'headerline'
        END_OF_LINE     = "eol"
        MAX_LINES_PARSE = 'maxlines'
        LOAD_WITH_CHAR_ERR = 'charerror'
        APPEND          = 'append'

class eConn (object):
    SQLSERVER   = "sql"
    ORACLE      = "oracle"
    VERTICA     = "vertica"
    ACCESS      = "access"
    MYSQL       = "mysql"
    LITE        = "sqlite"
    FILE        = "file"
    NONO        = 'nono'


    class dataType(object):
        B_STR = 'str'
        B_INT = 'int'
        B_FLOAT = 'float'
        B_LONG_STR = 'text'

        DB_VARCHAR  = 'varchar'
        DB_VARCHAR_MAX='varchar(MAX)'
        DB_NVARCHAR = 'nvarchar'
        DB_CHAR     = 'char'
        DB_BLOB     = 'blob'
        DB_INT      = 'int'
        DB_BIGINT   = 'bigint'
        DB_FLOAT    = 'float'
        DB_NUMERIC = 'numeric'
        DB_DECIMAL = 'decimal'
        DB_DATE     = 'datetime1'

class eSql (object):
    RENAME      = 'rename'
    DROP        = 'drop'
    TRUNCATE    = 'truncate'
    STRUCTURE   = 'structure'
    MERGE       = 'merge'
    ISEXISTS    = 'isexists'
    DELETE      = 'delete'

""" Methods To use for fun """
def findProp (prop, obj=eConn, dictProp=None):
    dicClass = obj.__dict__
    def getPropValue (prop):
        if prop:
            for p in dicClass:
                if isinstance(dicClass[p], str) and dicClass[p].lower() == prop.lower():
                    return prop

                if isinstance(dicClass[p], dict):
                    for k in dicClass[p]:
                        if dicClass[p][k] and prop in dicClass[p][k]:
                            return k
        return None

    ret = getPropValue (prop)
    if ret is not None:
        return ret
    if ret is None and dictProp and isinstance(dictProp ,(dict,OrderedDict)):
        keys = list(dictProp.keys())
        for k in keys:
            ret = getPropValue(k)
            if ret is not None:
                return ret
    return None


def getAllProp (obj=eJson):
    dicClass = obj.__dict__
    ret = []
    for p in dicClass:
        if '__' not in p and isinstance(dicClass[p], str):
            ret.append ( dicClass[p] )
    return ret