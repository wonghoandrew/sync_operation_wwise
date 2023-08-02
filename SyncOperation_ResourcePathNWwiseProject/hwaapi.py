from waapi import WaapiClient, CannotConnectToWaapiException

class hwaapi:
    '''需要waapi_connect方法进行连接'''
    def __init__(self) -> None:
        pass
    try:
        client = WaapiClient()
        print("已自动连接Wwise!")
        print("--------------------------------------------")
    except CannotConnectToWaapiException:
        print("--------------------------------------------")
        print("请打开wwise工程并重新连接")

    def _reopenwwise_please():
        hwaapi._fgx()
        print("请打开wwise工程并重新连接")

    def _fgx():
        print("--------------------------------------------")

    def waapi_connect():
        '''waapi接口，进行本地端口连接'''
        if hwaapi.waapi_isconnect_ornot() == None:
            try:
                hwaapi.client = WaapiClient()
                print('成功连接Wwise!')
            except CannotConnectToWaapiException:
                hwaapi._reopenwwise_please()
        elif hwaapi.waapi_isconnect_ornot() == False:
            try:
                hwaapi.client = WaapiClient()
            except CannotConnectToWaapiException:
                hwaapi._reopenwwise_please()
            print("成功连接Wwise!")
        elif hwaapi.waapi_isconnect_ornot() == True:
            print("已连接Wwise!")

    def waapi_disconnect():
        '''waapi接口，进行本地端口端口断开'''
        if hwaapi.waapi_isconnect_ornot() == None:
            hwaapi._reopenwwise_please()
        elif hwaapi.waapi_isconnect_ornot() == False:
            print("已断开Wwise!")
        elif hwaapi.waapi_isconnect_ornot() == True:
            hwaapi.client.disconnect()
            print("成功断开Wwise!")

    def waapi_isconnect_ornot():
        try:
            ornot = hwaapi.client.is_connected()
        except:
            ornot = None
        return ornot

class HWAQL:
    def __init__(self) -> None:
        pass

    ver_2019 = False

    rtopts = {
        "return":[
            "id",
            "name",
            "notes",
            "path",
            "type",
            "@ActionType",
            "@Target",
            "parent",
            "sound:originalWavFilePath",
            "audioSource:language"
        ]
    }

    def find_object(ID_or_Path:str,rt_str=False,rtopts=rtopts):
        waql_arg = {
            "waql":"from object \"%s\""%(ID_or_Path)
        }
        if rt_str:
            return waql_arg['waql']
        if HWAQL.ver_2019 == True:
            waql_arg = {
                'from':{
                    'path':[ID_or_Path]
                }
            }
        return AK_API.object_get(waql_arg,rtopts)

    def find_wav_referencesTo(or_wavfile_path:str,rt_str=False,rtopts=rtopts):#寻找哪些Object引用了该系统路径的音频
        waql_arg = {
            "waql":"from type Sound where originalWavFilePath : \"%s\""%(or_wavfile_path)
        }
        if rt_str:
            return waql_arg['waql']
        return AK_API.object_get(waql_arg,rtopts)

    def find_object_referencesTo(ID_or_Path:str,rt_str=False,rtopts=rtopts):#寻找该Object被应用的Object
        waqlstr = HWAQL.find_object(ID_or_Path,rt_str=True)
        waqlstr = waqlstr + "select referencesTo"
        waql_arg = {
            "waql":waqlstr
        }
        if rt_str:
            return waql_arg['waql']
        return AK_API.object_get(waql_arg,rtopts)

    def find_object_children(ID_or_Path:str,rt_str=False,rtopts=rtopts):
        waqlstr = HWAQL.find_object(ID_or_Path,True)
        waqlstr = waqlstr + "select children"
        waql_arg = {
            'waql':waqlstr
        }
        if rt_str:
            return waql_arg["waql"]
        if HWAQL.ver_2019 == True:
            waql_arg = {
                'from':{
                    'path':[ID_or_Path]
                },
                'transform':[
                    {
                        'select':['children']
                    }
                ]
            }
        return AK_API.object_get(waql_arg,rtopts)

    def find_object_descendants_except(ID_or_Path:str,rt_str=False,rtopts=rtopts,except_object_type="",*args:str):
        waqlstr = HWAQL.find_object(ID_or_Path,rt_str=True)
        waqlstr = waqlstr + " select descendants where type!=\"%s\""%(except_object_type)
        for i in args:
            waqlstr = waqlstr + " and type != \"%s\""%(i)
        waql_arg = {"waql":waqlstr}
        if rt_str:
            return waql_arg["waql"]
        return AK_API.object_get(waql_arg,rtopts)

    def find_object_descendants_select(ID_or_Path:str,rt_str=False,rtopts=rtopts,select_object_type=""):
        waqlstr = HWAQL.find_object(ID_or_Path,rt_str=True)
        waqlstr = waqlstr + " select descendants where type = \"%s\""%(select_object_type)
        waql_arg = {
            'waql':waqlstr
        }
        if rt_str:
            return waql_arg["waql"]
        return AK_API.object_get(waql_arg,rtopts)

    def find_object_name(STR_name:str,rt_str=False,rtopts=rtopts):
        waqlstr = "$ where name : \"%s\""%(STR_name)
        waql_arg = {"waql":waqlstr}
        if rt_str:
            return waql_arg['waql']
        return AK_API.object_get(waql_arg,rtopts)

class AK_API:
    '''封装的API以2021的版本作为标准'''
    def __init__(self) -> None:
        pass

    hwaapi = hwaapi

    rtopts = {
        "return":[
            "id",
            "name",
            "notes",
            "path",
            "type",
            "@ActionType",
            "@Target",
            "parent",
            "sound:originalWavFilePath",
            "audioSource:language"
        ]
    }
    def audio_import(data:dict,rtopts=rtopts):
        rt = AK_API.hwaapi.client.call("ak.wwise.core.audio.import",data,options=rtopts)
        if rt != None:
            rt = rt['objects']
        return rt

    def object_get(data:dict,rtopts=rtopts):
        rt = AK_API.hwaapi.client.call("ak.wwise.core.object.get",data,options=rtopts)
        if rt != None:
            rt = rt['return']
        return rt

    def object_create(data:dict):
        return AK_API.hwaapi.client.call("ak.wwise.core.object.create",data)
    def object_delete(data:dict):
        return AK_API.hwaapi.client.call("ak.wwise.core.object.delete",data)
    def object_move(data:dict):
        return AK_API.hwaapi.client.call("ak.wwise.core.object.move",data)
    def object_copy(data:dict):
        return AK_API.hwaapi.client.call("ak.wwise.core.object.copy",data)

    def object_setName(data:dict):
        return AK_API.hwaapi.client.call("ak.wwise.core.object.setName",data)

    def switchContainer_addAssignment(data:dict):
        return AK_API.hwaapi.client.call("ak.wwise.core.switchContainer.addAssignment",data)

    def ui_getSelectedObjects(rtopts=rtopts):
        rt = AK_API.hwaapi.client.call("ak.wwise.ui.getSelectedObjects",options=rtopts)
        if rt != None:
            rt = rt['objects']
        return rt

    def object_setReference(data:dict):
        return AK_API.hwaapi.client.call("ak.wwise.core.object.setReference",data)

    def object_setProperty(data:dict):
        return AK_API.hwaapi.client.call("ak.wwise.core.object.setProperty",data)

    def getInfo():
        return AK_API.hwaapi.client.call("ak.wwise.core.getInfo",{})

    def log_get(data:dict):
        '''
        soundbankGenerate,conversion,
        copyPlatformSettings,waapi,
        projectLoad,general
        '''
        return AK_API.hwaapi.client.call("ak.wwise.core.log.get",data)

class OBJ_Reference:
    ContainerType = ["Folder","WorkUnit","ActorMixer","RandomSequenceContainer","SwitchContainer","BlendContainer"]
    SoundType = ["Sound"]

