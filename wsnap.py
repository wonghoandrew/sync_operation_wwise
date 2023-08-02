#-*- coding: utf-8 -*-
from hwaapi import HWAQL,AK_API
from queue import Queue
from datetime import datetime
from pprint import pprint
import os, threading
import time
import PySimpleGUI as sg
from watchdog.observers import Observer
from watchdog.events import *
from watchdog.utils.dirsnapshot import DirectorySnapshot, DirectorySnapshotDiff

class FileEventHandler(FileSystemEventHandler):
    def __init__(self, aim_path):
        FileSystemEventHandler.__init__(self)
        self.aim_path = aim_path
        self.timer = None
        self.snapshot = DirectorySnapshot(self.aim_path)

    lock = threading.Lock()

    def on_any_event(self, event):
        if self.timer:
            self.timer.cancel()
        with FileEventHandler.lock:
            self.timer = threading.Timer(0.2, self.checkSnapshot)
        self.timer.start()
        self.timer.join()
        # if HWAAPI.AutoImport:
        #     HWAAPI.AKIMPORT_TEST()

    def select_wav(lis):
        for il in lis:
            if isinstance(il,tuple):
                if os.path.splitext(il[0])[1] == '.wav' or os.path.splitext(il[0])[1] == '':
                    yield [il[0],il[1]]
            else:
                if os.path.splitext(il)[1] == '.wav' or os.path.splitext(il)[1] == '':
                    yield il

    def checkSnapshot(self):
        '''快照，得到监控中文件夹被操作时的动作类型,并传输给Transfer.Act=Queue()'''
        snapshot = DirectorySnapshot(self.aim_path)
        diff = DirectorySnapshotDiff(self.snapshot, snapshot)
        self.snapshot = snapshot
        self.timer = None
        contain = {}
        contain.update({"files_created":[i for i in FileEventHandler.select_wav(diff.files_created)]})
        contain.update({"files_deleted":[i for i in FileEventHandler.select_wav(diff.files_deleted)]})
        contain.update({"files_moved":  [i for i in FileEventHandler.select_wav(diff.files_moved)]})
        contain.update({"files_modified":[i for i in FileEventHandler.select_wav(diff.files_modified)]})
        contain.update({"dirs_created":[i for i in FileEventHandler.select_wav(diff.dirs_created)]})
        contain.update({"dirs_deleted":[i for i in FileEventHandler.select_wav(diff.dirs_deleted)]})
        contain.update({"dirs_moved":  [i for i in FileEventHandler.select_wav(diff.dirs_moved)]})
        contain.update({"dirs_modified":[i for i in FileEventHandler.select_wav(diff.dirs_modified)]})

        snapaction = {
            "activity":[contain],
            "time":str(datetime.now().strftime(r"%m/%d/%Y %H:%M:%S.%f"))
        }

        Contain = False
        for i in snapaction["activity"][0]:
            if snapaction["activity"][0][i] != []:
                Contain = True
        if Contain:
            if HWAAPI.AutoImport:
                Transfer.Act.put(snapaction)
            #print(snapaction)

class Transfer:
    '''用于处理数据的类'''
    def __init__(self) -> None:
        self.loop_transfer = threading.Thread(target=Transfer.Transfer)
        '''新开线程并循环检测并传输处理数据'''
        self.Act = Transfer.Act
        self.Action = Transfer.Action
        pass

    Act = Queue()

    Action = Queue()

    def cal_time(t1):
        '''转换时间格式'''
        temptime1 = datetime.strptime(t1,r'%m/%d/%Y %H:%M:%S.%f')
        return int(time.mktime(temptime1.timetuple()) * 1000.0 + (temptime1.microsecond / 1000.0))

    def Transfer():
        '''用于线程循环进行数据处理以及传输'''
        while HWAAPI.AutoImport:
            time.sleep(0.1)
            Transfer.Ar()
            time.sleep(0.1)
            Transfer.Ip()

    def Ar():
        '''从Transfer.Act得到数据，归类动作数据并进行整理成行为，完成后传输到Transfer.Action=Queue()'''
        if not Transfer.Act.empty():
            data = Transfer.ArrangeAction(Transfer.Act.get())
            Transfer.Action.put(data)

    def Ip():
        '''从Transfer.Action得到数据，处理行为数据并转化成waapi可用的json数据结构，完成后传输到Imports.Import=Queue()'''
        if not Transfer.Action.empty():
            data = Transfer.ImportTypeSwitch(Transfer.Action.get())
            HWAAPI.Import.put(data)

    def _ActionType(NoneAct=list):
        '''
        用于分辨三种操作三种情况得出行为结果：
        操作(created/deleted/moved)
        情况(files/dirs/both)
        '''
        if 'dirs_moved' not in NoneAct:
            if 'files_moved' not in NoneAct:
                return 'both_moved'
            else:
                return 'dirs_moved'
        elif 'files_moved' not in NoneAct and 'dirs_moved' in NoneAct:
            return 'files_moved'
        
        elif 'dirs_created' not in NoneAct:
            if 'files_created' not in NoneAct:
                return 'both_created'
            else:
                return 'dirs_created'
        elif 'files_created' not in NoneAct and 'dirs_created' in NoneAct:
            return 'files_created'

        elif 'dirs_deleted' not in NoneAct:
            if 'files_deleted' not in NoneAct:
                return 'both_deleted'
            else:
                return 'dirs_deleted'
        elif 'files_deleted' not in NoneAct and 'dirs_deleted' in NoneAct:
            return 'files_deleted'

        else:
            return "WRONG_Action"

    def ArrangeAction(data):
        '''归类动作数据并进行整理成行为'''
        iAct = data
        #print(iAct)
        iAct.update({"caltime":Transfer.cal_time(iAct['time'])})
        NoneAct = []
        for iactivity in list(iAct['activity'][0].keys()):
            iactionlist = iAct['activity'][0][iactivity]
            if iactionlist == []:
                NoneAct.append(iactivity)
                del iAct['activity'][0][iactivity]
            else:
                language = ""
                if '\\Originals\\SFX' in iactionlist[0]:
                    iAct.update({"language":"SFX"})
                    language = 'SFX'
                elif '\\Originals\\Voices' in iactionlist[0]:#出现错误
                    language = iactionlist[0].split('\\Originals\\Voices\\')[1].split('\\')[0]
                    iAct.update({"language":language})
                else:
                    try:
                        if '\\Originals\\SFX' in iactionlist[0][0]:
                            iAct.update({"language":"SFX"})
                            language = 'SFX'
                        elif '\\Originals\\Voices' in iactionlist[0][0]:#出现错误
                            language = iactionlist[0][0].split('\\Originals\\Voices\\')[1].split('\\')[0]
                            iAct.update({"language":language})
                        else:
                            iAct.update({"language":"WRONG_language"})
                    except:
                        iAct.update({"language":"WRONG_language"})

                for iactionnumber in range(len(iactionlist)):
                    temp = iactionlist[iactionnumber]
                    if language == 'SFX':
                        if isinstance(temp, list):
                            iactionlist[iactionnumber][0] = temp[0].split("\\Originals\\SFX")[1]
                            iactionlist[iactionnumber][1] = temp[1].split("\\Originals\\SFX")[1]
                        else:
                            iactionlist[iactionnumber] = temp.split("\\Originals\\SFX")[1]
                    else:
                        if isinstance(temp, list):
                            iactionlist[iactionnumber][0] = temp[0].split("\\Originals\\Voices\\"+language)[1]
                            iactionlist[iactionnumber][1] = temp[1].split("\\Originals\\Voices\\"+language)[1]
                        else:
                            iactionlist[iactionnumber] = temp.split("\\Originals\\Voices\\"+language)[1]
        iAct.update({'monitor_path':DirMonitor.Aim_Path})
        iAct.update({'type':Transfer._ActionType(NoneAct)})
        #print(iAct)
        return iAct

    def ActionTypeSwitch(type):
        '''中转，用于根据行为类型选择waapi_json数据结构处理的方法'''
        swtich = {
                'files_moved':Transfer.files_moved,
                'dirs_moved':Transfer.dirs_moved,
                'both_moved':Transfer.both_moved,
                'files_created':Transfer.files_created,
                'dirs_created':Transfer.dirs_created,
                'both_created':Transfer.both_created,
                'files_deleted':Transfer.files_deleted,
                'dirs_deleted':Transfer.dirs_deleted,
                'both_deleted':Transfer.both_deleted,
                'WRONG_Action':Transfer.wrong_action,
            }
        return swtich[type]

    def ImportTypeSwitch(data):
        '''将waapi数据与之前的行为数据进行整合'''
        ip = {
            'Actions':data,
            'Hwaapi':Transfer.ActionTypeSwitch(data['type'])(data),
        }
        return ip

    '''移动部分(可能含改名的部分)'''
    def files_moved(data):
        _move_args = []
        _rename_args = []
        for im in data['activity'][0]['files_moved']:
            im_1 = r"\Actor-Mixer Hierarchy\Default Work Unit" + os.path.splitext(im[0])[0]
            if im[0].rsplit("\\",1)[0] == im[1].rsplit("\\",1)[0]:
                im_2 = os.path.splitext(im[1])[0].rsplit("\\",1)[1]
                _rename_args.append(
                    {
                        'object':im_1,'value':im_2
                    }
                )
            else:
                im_2 = r"\Actor-Mixer Hierarchy\Default Work Unit" + im[1].rsplit("\\",1)[0]
                _move_args.append(
                    {
                        'object':im_1,'parent':im_2,'onNameConflict':'rename'
                    }
                )
        if len(_move_args) > 0 and len(_rename_args) == 0:
            return _move_args
        elif len(_move_args) == 0 and len(_rename_args) > 0:
            return _rename_args
        else:
            return []

    def dirs_moved(data):
        _move_args = []
        _rename_args = []
        for im in data['activity'][0]['dirs_moved']:
            im_1 = r"\Actor-Mixer Hierarchy\Default Work Unit" + im[0]
            if im[0].rsplit("\\",1)[0] == im[1].rsplit("\\",1)[0]:#重命名
                im_2 = im[1].rsplit("\\",1)[1]
                _rename_args.append(
                    {
                        'object':im_1,'value':im_2
                    }
                )
            else:
                im_2 = r"\Actor-Mixer Hierarchy\Default Work Unit" + im[1].rsplit("\\",1)[0]
                _move_args.append(
                    {
                        'object':im_1,'parent':im_2,'onNameConflict':'rename'
                    }
                )
        return [_rename_args,_move_args]

    def both_moved(data):
        dirs_files_import = []
        dirs_files_import.append(Transfer.dirs_moved(data))
        dirs_files_import.append(Transfer.files_moved(data))
        return dirs_files_import

    '''添加部分'''
    def files_created(data):
        _imports = []
        if data['language'] == 'SFX':
            language = '\\SFX'
        else:
            language = '\\Voices\\'+data['language']

        for iaudio in data['activity'][0]['files_created']:
            audiofile = data['monitor_path'] + language + iaudio
            objpath = os.path.splitext(iaudio)[0]
            if data['language'] != 'SFX':#非2019
                pth = objpath.rsplit("\\",1)[0]
                nme = objpath.rsplit("\\",1)[1]
                objpath = pth + '\\<AudioFileSource>' + nme
            else:
                pth = objpath.rsplit("\\",1)[0]
                nme = objpath.rsplit("\\",1)[1]
                objpath = pth + '\\<AudioFileSource>' + nme
            _imports.append({
                'audioFile':audiofile,
                'objectPath':objpath,
                #'objectType':'Sound',
                'importLanguage':data['language'],
            })

        import_args = {
            "importOperation": "useExisting",  # 创建新的对象；若存在同名的现有对象，则将现有对象销毁。
            "default": {
                #"importLanguage": data['language'],
                "importLocation":r"\Actor-Mixer Hierarchy\Default Work Unit",
                },
            "imports": _imports
        }
        return import_args

    def dirs_created(data):
        def containerType(string):#用于定义在文件夹命名上填写container类型命名规则，暂时所有默认ActorMixer
            string = 'ActorMixer'
            return string
        def children_args(Args_list:list):#将单个路径组成单个json导入格式——暂时没用，以后可能要用
            done_list = []
            def args_create(objpth,arg={}):
                children = {}
                if objpth == '':
                    return arg
                try:
                    foldername = objpth.rsplit('\\',1)[1]
                except:
                    return arg
                folderpath = objpth.rsplit('\\',1)[0]
                if len(arg) > 0:
                    children.update({'children':[arg]})
                children.update({'name':foldername,'type':'ActorMixer'})
                return args_create(folderpath,children)
            for ia in Args_list:
                done_list.append(args_create(ia))
            return done_list
        def children_merge(datas):#将列表中的字符串整合成一个导入模块，用的是这个
            def find_bottom_paths(paths):
                # 将路径转化为元组
                path_tups = [tuple(path.split('\\')) for path in paths]
                bottom_paths = []
                for path_tup in path_tups:
                    # 判断当前路径是否为底层目录
                    is_bottom = True
                    for other_tup in path_tups:
                        # 判断当前路径是否是其他路径的上级目录
                        if path_tup != other_tup and path_tup[:len(other_tup)] == other_tup:
                            is_bottom = False
                            break
                    # 如果当前路径是底层目录，则加入到结果列表中
                    if is_bottom:
                        bottom_paths.append('\\'.join(path_tup))
                return bottom_paths
            need_args = find_bottom_paths(datas)
            def create_nested_dict(paths):
                def convert_to_tree_structure(root):
                    tree = []
                    for k, v in root.items():
                        node = {"name": k}
                        kname = containerType(k)
                        node.update({'type':kname})
                        if v:
                            node["children"] = convert_to_tree_structure(v)
                        tree.append(node)
                    return tree

                root = {}
                for path in paths:
                    parts = path.split("\\")[1:]
                    node = root
                    for part in parts:
                        if part not in node:
                            node[part] = {}
                        node = node[part]
                return convert_to_tree_structure(root)

            return create_nested_dict(need_args)
        _importpath = []
        for ifolder in sorted(data['activity'][0]['dirs_created'],key=lambda x : x.count("\\")):
            _importpath.append(ifolder)
        #_imports = children_args(_importpath)
        children_arg = children_args(_importpath)
        import_args_list = []
        for ii in children_arg:
            import_args = {
                'parent':r"\Actor-Mixer Hierarchy",
                'onNameConflict':'merge',
                'type':'WorkUnit',
                'name':'Default Work Unit',
                'children':[ii]
            }
            import_args_list.append(import_args)
        return import_args_list

    def both_created(data):
        dirs_files_import = []
        dirs_files_import.append(Transfer.dirs_created(data))
        dirs_files_import.append(Transfer.files_created(data))
        return dirs_files_import

    '''删除部分'''
    def files_deleted(data):
        _delete = []
        for iaudio in data['activity'][0]['files_deleted']:
            objpath = r"\Actor-Mixer Hierarchy\Default Work Unit" + os.path.splitext(iaudio)[0]
            _delete.append(
                {
                    'object':objpath
                }
            )
        return _delete

    def dirs_deleted(data):
        _delete = []
        for idir in data['activity'][0]['dirs_deleted']:
            objpath = r"\Actor-Mixer Hierarchy\Default Work Unit" + os.path.splitext(idir)[0]
            _delete.append(
                {
                    'object':objpath
                }
            )
        return _delete

    def both_deleted(data):
        dirs_files_import = []
        dirs_files_import.append(Transfer.dirs_deleted(data))
        dirs_files_import.append(Transfer.files_deleted(data))
        return dirs_files_import

    def wrong_action(data):
        return None



class HWAAPI:
    def __init__(self) -> None:
        self.loop_akimport = threading.Thread(target=HWAAPI.AkImport)
        '''新开线程并循环检测并导入工程'''
        self.Import = HWAAPI.Import
        self.WwiseReturns = HWAAPI.WwiseReturns
        pass

    rtopts = {
        'return':['id','name','type','filePath','parent','path','sound:originalWavFilePath','@target']
    }

    AutoImport = True
    try:
        waapiclient = AK_API.hwaapi.client
    except:
        ""
    Import = Queue()

    WwiseReturns = Queue()

    skip_ask = False
    '''是否跳过'''

    input_s = "0"
    '''0为继续，1为忽略'''

    def inputcheck(skip_ask=False,input_s="0"):
        if not skip_ask:
            s = input()
            if s == "0":
                return True
            elif s == "1":
                return False
            elif s == "2":
                HWAAPI.skip_ask=True
                input_s="0"
                return True
            elif s == "3":
                HWAAPI.input_s=False
                input_s="1"
                return False
            else:
                print("请输入正确指令")
                return HWAAPI.inputcheck(skip_ask=False)
        else:
            if input_s == "0":
                return True
            elif input_s == "1":
                return False
            else:
                print("请输入正确指令")
                return HWAAPI.inputcheck(skip_ask=False)

    def reset_inputcheck():
        HWAAPI.skip_ask = False
        HWAAPI.input_s = "0"

    def AKIMPORT_TEST():
        ""
        Transfer.Ar()
        Transfer.Ip()
        if not HWAAPI.Import.empty():
            data = HWAAPI.Import.get()
            data = HWAAPI.Import_TypeToDo(data)
            print(data)
    '''--------------------------------------------'''

    def AkImport():#循环导入的线程
        '''用于线程循环检测Import是否有内容，有则导入。'''
        while HWAAPI.AutoImport:
            time.sleep(0.1)
            if not HWAAPI.Import.empty():
                data = HWAAPI.Import.get()
                dt = HWAAPI.Import_TypeToDo(data)
                print("--------------------------------------------")
                print(dt)

    def Import_TypeToDo(data):
        '''中转，用于选择导入类型，并进行用API导入工程'''
        #注释的都是还没做完的
        switch = {
            'files_moved':HWAAPI.waapi_files_moved,
            'dirs_moved':HWAAPI.waapi_dirs_moved,
            'both_moved':HWAAPI.waapi_both_moved,
            'files_created':HWAAPI.waapi_files_created,
            'dirs_created':HWAAPI.waapi_dirs_created,
            'both_created':HWAAPI.waapi_both_created,
            'files_deleted':HWAAPI.waapi_files_deleted,
            'dirs_deleted':HWAAPI.waapi_dirs_deleted,
            'both_deleted':HWAAPI.waapi_both_deleted,
            'WRONG_Action':HWAAPI.waapi_wrong,
        }
        return switch[data['Actions']['type']](data)

    def waapi_wrong(data):
        return data

    def _bug_reimport_delete_resource_dt(data):
        if data['Actions']['language'] == 'English(US)':
            as_reimport = []
            if data['Actions']['type'] == 'both_created':
                dt = data['Hwaapi'][1]['imports']
            else:
                dt = data['Hwaapi']['imports']
            for ias in dt:
                obj_audiosource = HWAQL.find_object_children(r"\Actor-Mixer Hierarchy\Default Work Unit" + ias['objectPath'])
                if obj_audiosource != None:
                    if 'English(US)' not in [ias_['audioSource:language']['name'] for ias_ in obj_audiosource]:
                        as_reimport.append(obj_audiosource)
                        for d_ias in obj_audiosource:
                            AK_API.object_delete({'object':d_ias['id']})
            return as_reimport

    def _bug_reimport_resource(data):
        if data == None:
            return
        for objs in data:
            for rs in objs:
                pth = rs['path'].rsplit('\\',1)[0]
                _imports={
                    'audioFile':rs['sound:originalWavFilePath'],
                    'objectPath':pth,
                    'objectType':'Sound',
                    'importLanguage':rs['audioSource:language']['name']
                    }
                import_args = {
                    "importOperation": "useExisting",  # 创建新的对象；若存在同名的现有对象，则将现有对象
                    "imports": [_imports]
                }
                AK_API.audio_import(import_args)

    '''添加部分'''
    def waapi_files_created(data):
        #rt_objs = HWAAPI._bug_reimport_delete_resource_dt(data)
        rts = AK_API.audio_import(data['Hwaapi'])
        #HWAAPI._bug_reimport_resource(rt_objs)
        data.update({'Returns':rts})
        return data
    def waapi_dirs_created(data):
        rts = []
        for i in data['Hwaapi']:
            rts.append(AK_API.object_create(i))
        data.update({'Returns':rts})
        return data
    def waapi_both_created(data):
        allrts = []
        rts1 = []
        for i in data['Hwaapi'][0]:
            rts2_i = AK_API.object_create(i)
            rts1.append(rts2_i)
        time.sleep(0.1)
        #rt_objs = HWAAPI._bug_reimport_delete_resource_dt(data)
        rts2 = AK_API.audio_import(data['Hwaapi'][1])
        #HWAAPI._bug_reimport_resource(rt_objs)
        allrts.append(rts1)
        allrts.append(rts2)
        data.update({'Returns':allrts})
        return data

    '''删除部分'''
    def waapi_files_deleted(data):
        allrts = []
        not_imports_wav = []#没导入进
        imports_rfrc = []#有导入但路径不对应且音频有被引用的无用路径
        pr_imports_rfrc = []
        for id in data['Hwaapi']:
            rtswaqlobj = HWAQL.find_object(id['object'])
            if rtswaqlobj == None:
                filepth = data['Actions']['monitor_path']+"\\"+data['Actions']['language']+id['object'].split(r"\Actor-Mixer Hierarchy\Default Work Unit",1)[1]+".wav"
                rtswaqlobj = HWAQL.find_wav_referencesTo(filepth)
                if len(rtswaqlobj) < 1:
                    not_imports_wav.append(filepth)
                else:
                    imports_rfrc.append(rtswaqlobj)
                    t = []
                    t.append(filepth)
                    t.append(rtswaqlobj)
                    pr_imports_rfrc.append(t)
            else:
                rtswaqlrts = HWAQL.find_object_referencesTo(id['object'])
                rtswaqlobj[0].update({'referencesTo':rtswaqlrts})
                AK_API.object_delete(id)
                allrts.append(rtswaqlobj[0])
        if len(not_imports_wav) > 0:
            print('--------------------------------------------')
            print("WARNING:以下删除文件夹内的音频找不到对应的SoundObject，可能之前没导入进工程内")
            for i in not_imports_wav:
                print(i)
        if len(pr_imports_rfrc) > 0:
            print('--------------------------------------------')
            print("WARNING:以下SoundObject路径与音频路径不对应，这些是引用了已删除音频的SoundObject")
            for irfrc in pr_imports_rfrc:
                p = irfrc[0]+r":$"
                for objpth in irfrc[1]:
                    p = p + "\"%s\","%(objpth['id'])
                p = p.rsplit(",",1)[0]
                print(p)
            print("以上是音频以及引用音频的SoundObject，请将音频路径冒号后面的字符串复制到wwise的搜索栏中进行查看")
        data.update({'Returns':allrts})
        return data
    def waapi_dirs_deleted(data):
        c_dt = data['Hwaapi']
        data['Hwaapi'] = [c_dt,[]]
        return HWAAPI.waapi_both_deleted(data)
    def waapi_both_deleted(data):
    #方案一
    #从所删除文件夹对应的Object-container中的子集Object-container循环算起
    #该Object-container是否有含有对应的文件夹
    #该Object-container是否有含有Sound-Object
    #该Sound-Object是否含有所对应的音频
    #该音频又是否在所删除的文件夹内

    #关于Object-container是否有所对应的文件夹这一事件，若没有则自动移动到_temp 中待定
    #以及其中所删除的Sound-Object是否有所对应的音频但没有在所删的则自动移动到_temp 中待定
        not_imports_in_wwise = []#没导入进工程且检测不到
        not_samepth_in_wwise = []#有导入但路径是不同的
        dl_sound_obj = []
        dl_ctnr_obj = []

        pth_sound_obj = []
        for ids in data['Hwaapi'][1]:
            find_obj = HWAQL.find_object(ids['object'])
            if find_obj == None:
                filepth = data['Actions']['monitor_path']+"\\"+data['Actions']['language']+ids['object'].split(r"\Actor-Mixer Hierarchy\Default Work Unit",1)[1]+".wav"
                rts_rfrct_obj = HWAQL.find_wav_referencesTo(filepth)
                if len(rts_rfrct_obj) < 1:
                    not_imports_in_wwise.append(filepth)
                else:
                    t = []
                    t.append(filepth)
                    t.append(rts_rfrct_obj)
                    not_samepth_in_wwise.append(t)
            else:
                pth_sound_obj.append(find_obj[0]['path'])
                rts_rfrc = HWAQL.find_wav_referencesTo(find_obj[0]['id'])
                find_obj[0].update({'referencesTo':rts_rfrc})
                dl_sound_obj.append(find_obj[0])

        if len(not_imports_in_wwise) > 0:
            print('--------------------------------------------')
            print("WARNING:以下删除文件夹内的音频找不到对应的SoundObject，可能之前没导入进工程内")
            for i in not_imports_in_wwise:
                print(i)
        if len(not_samepth_in_wwise) > 0:
            print('--------------------------------------------')
            print("WARNING:以下删除的SoundObject路径与音频路径不对应，这些是引用了已删除音频的SoundObject")
            for irfrc in not_samepth_in_wwise:
                p = irfrc[0]+r":$"
                for objpth in irfrc[1]:
                    p = p + "\"%s\","%(objpth['id'])
                p = p.rsplit(",",1)[0]
                print(p)
            print("以上是音频以及引用音频的SoundObject，请将音频路径冒号后面的字符串复制到wwise的搜索栏中进行查看")
        not_fdlr_findin_wwctnr = []

        for idirpth in data['Hwaapi'][0]:
            find_obj = HWAQL.find_object(idirpth['object'])
            #print(find_obj)
            if find_obj == None:
                filepth = data['Actions']['monitor_path']+"\\"+data['Actions']['language']+idirpth['object'].split(r"\Actor-Mixer Hierarchy\Default Work Unit",1)[1]
                not_fdlr_findin_wwctnr.append(filepth)
            else:
                dl_ctnr_obj.append(find_obj[0])

        if len(not_fdlr_findin_wwctnr) > 0:
            print('--------------------------------------------')
            print("WARNING:以下这些删除的文件夹找不到对应的ObjectContainer，可能之前没有导入进工程内")
            for i in not_fdlr_findin_wwctnr:
                print(i)
        def find_bottom_top_paths(paths):
            # 将路径转化为元组
            path_tups = [tuple(path.split('\\')) for path in paths]
            bottom_paths = []
            top_paths = []
            for path_tup in path_tups:
                # 判断当前路径是否为底层目录
                is_bottom = True
                for other_tup in path_tups:
                    # 判断当前路径是否是其他路径的上级目录
                    if path_tup != other_tup and path_tup[:len(other_tup)] == other_tup:
                        is_bottom = False
                        break
                # 如果当前路径是底层目录，则加入到结果列表中
                if is_bottom:
                    bottom_paths.append('\\'.join(path_tup))
                else:
                    top_paths.append('\\'.join(path_tup))
            return [bottom_paths,top_paths]

        bt_top_dt = find_bottom_top_paths([i['object'] for i in data['Hwaapi'][0]])
        need_data = bt_top_dt[0]
        delets_data = bt_top_dt[1]

        _descendants_still = []
        for i_find_descendants in need_data:
            descendants = HWAQL.find_object_descendants_except(i_find_descendants,except_object_type="AudioFileSource")
            if descendants != None:
                for idsdts in descendants:
                    #print(idsdts)
                    if idsdts['type'] == 'Sound':
                        if idsdts['path'] not in delets_data and idsdts['path'] not in pth_sound_obj and idsdts['path'] not in _descendants_still:
                            _descendants_still.append(idsdts)
                    else:
                        if idsdts['path'] not in delets_data and idsdts['path'] not in need_data and idsdts['path'] not in _descendants_still:
                            _descendants_still.append(idsdts)

        if len(_descendants_still) > 1:
            parent = r"\Actor-Mixer Hierarchy\Default Work Unit"
            t_time = str(datetime.now().strftime(r"%y%m%d_%H%M%S"))
            print('--------------------------------------------')
            print(r"WARNING:")
            print(r"请查看\Actor-Mixer Hierarchy\Default Work Unit\__temp"+"\\"+t_time+r"位置,")
            print(r"存在不属于所删文件夹关联的Object。")
            creat_args = {
                'parent':parent,
                'onNameConflict':'merge',
                'type':'Folder',
                'name':'__temp',
                'notes':"WAAPI处理剩下的Object",
                'children':[{
                    'name':t_time,
                    'type':'Folder',
                    'notes':"不属于上次所删文件夹关联的Object"
                }]
            }
            AK_API.object_create(creat_args)
            parent = parent +"\\__temp\\" + t_time
            for i_move in _descendants_still:
                i_move['id']
                AK_API.object_move({"object":i_move['id'],"parent":parent,"onNameConflict": "rename"})
        for i_delete in need_data:
            AK_API.object_delete({'object':i_delete})
        data.update({'Returns':[dl_ctnr_obj,dl_sound_obj]})
        return data

    '''移动部分'''
    def waapi_files_moved(data):
        not_imports_wav = []#没有导入的
        others_imports_rfrcs = []#音频路径及其被引用的所有SoundObject
        true_move_rename = []
        #方案一：
        #移动后需要直接导入所有其爆红的，可以直接使用Hwaapi里的数据做。
        #导入爆红了的后，用音频移动前的路径检测其他SoundObject引用该音频的其他SoundObject路径。
        #之后就实施移动api，将合理的SoundObject移到对应的地方。
        Rename_Move_ornot = True
        if 'value' in data['Hwaapi'][0].keys():
            Rename_Move_ornot = True
        elif 'parent' in data['Hwaapi'][0].keys():
            Rename_Move_ornot = False
        _imports = []
        for i_p in data['Hwaapi']:#rename以及move的导入爆红。
            fpth_old = data['Actions']['monitor_path']+"\\"+data['Actions']['language']+i_p['object'].split(r"\Actor-Mixer Hierarchy\Default Work Unit",1)[1]+".wav"
            if Rename_Move_ornot:
                fpth_new = data['Actions']['monitor_path']+"\\"+data['Actions']['language']+i_p['object'].split(r"\Actor-Mixer Hierarchy\Default Work Unit",1)[1].rsplit("\\",1)[0]+"\\"+i_p['value']+".wav"
            else:
                fpth_new = data['Actions']['monitor_path']+"\\"+data['Actions']['language']+i_p['parent'].split(r"\Actor-Mixer Hierarchy\Default Work Unit",1)[1]+"\\"+fpth_old.rsplit("\\",1)[1]
            i_p_rfrc = HWAQL.find_wav_referencesTo(fpth_old)
            if len(i_p_rfrc) < 1:
                not_imports_wav.append(fpth_old)
            else:
                others_rfrc = []
                for rfrc in i_p_rfrc:
                    audiosources = HWAQL.find_object_children(rfrc['id'])
                    for i_a in audiosources:
                        AK_API.object_delete({'object':i_a['id']})
                    _imports.append(
                        {
                            'audioFile':fpth_new,
                            'objectPath':rfrc['path'],
                            'objectType':'AudioFileSource',
                        }
                    )
                    if rfrc['path'] != i_p['object']:
                        others_rfrc.append(rfrc)
                    else:
                        true_move_rename.append(i_p)
                if len(others_rfrc) > 0:
                    t = []
                    t.append(fpth_old+'-'+fpth_new)
                    t.append(others_rfrc)
                    others_imports_rfrcs.append(t)
        import_args = {
            "importOperation": "useExisting",  # 创建新的对象；若存在同名的现有对象，则将现有对象销毁。
            "default": {
                "importLanguage": data['Actions']['language'],
                "importLocation":r"\Actor-Mixer Hierarchy\Default Work Unit",
                },
            "imports":_imports
        }
        AK_API.audio_import(import_args)
        for i_m in true_move_rename:
            if Rename_Move_ornot:
                AK_API.object_setName(i_m)
            else:
                AK_API.object_move(i_m)
        if len(not_imports_wav) > 0:
            print('--------------------------------------------')
            print("WARNING:以下移动/重命名的音频找不到对应的SoundObject，可能之前没导入进工程内")
            for i in not_imports_wav:
                print(i)
        if len(others_imports_rfrcs) > 0:
            print('--------------------------------------------')
            print("WARNING:以下SoundObject路径与音频路径不对应，但是引用了已移动/重命名音频的SoundObject")
            for irfrc in others_imports_rfrcs:
                p = irfrc[0]+r":$"
                for objpth in irfrc[1]:
                    p = p + "\"%s\","%(objpth['id'])
                p = p.rsplit(",",1)[0]
                print(p)
            print("以上是音频以及引用音频的其他SoundObject，请将音频路径冒号后面的字符串复制到wwise的搜索栏中进行查看")
        return data
    def waapi_dirs_moved(data,checkSound=True):
        #方案一：
        #因为该文件夹内可能还包含有文件夹(没有音频)：
        #检测移动/重命名的文件夹的原路径是否对应在工程中有相应的路径√
        #检测移动/重命名的文件对应的containerObject是否含有其他东西√
        #检测完后打印警示，如果只是重命名的，重命名其文件夹√
        #如果是移动的，检测拿出其最父层级，只要移动这些就好了√

        not_imports_dir = []#没有导入进来的
        _imports_dir = []
        for i_r in data['Hwaapi'][0]:
            rts = HWAQL.find_object(i_r['object'])
            if rts == None:
                filepth = data['Actions']['monitor_path']+"\\"+data['Actions']['language'] + i_r['object'].split(r"\Actor-Mixer Hierarchy\Default Work Unit",1)[1]
                not_imports_dir.append(filepth)
            else:
                if i_r['object'] not in _imports_dir:
                    _imports_dir.append(i_r['object'])
        for i_m in data['Hwaapi'][1]:
            rts = HWAQL.find_object(i_m['object'])
            if rts == None:
                filepth = data['Actions']['monitor_path']+"\\"+data['Actions']['language'] + i_m['object'].split(r"\Actor-Mixer Hierarchy\Default Work Unit",1)[1]
                not_imports_dir.append(filepth)
            else:
                if i_m['object'] not in _imports_dir:
                    _imports_dir.append(i_m['object'])

        moves_ancestors = []
        _descendants_not_pair = []#所对应的重命名/移动对象的container的子集含有不关联的Object
        if len(data['Hwaapi'][0]) > 0:
            "单重命名"
            for i_dscdts in data['Hwaapi'][0]:
                if i_dscdts['object'] in _imports_dir:
                    i_ds = HWAQL.find_object_descendants_except(i_dscdts['object'],except_object_type="AudioFileSource")
                    for i_d in i_ds:
                        if i_d['path'] not in _imports_dir and i_d['path'] not in _descendants_not_pair:
                            _descendants_not_pair.append(i_d['id'])
        else:
            "有移动"
            def find_bottom_top_paths(paths):
                # 将路径转化为元组
                path_tups = [tuple(path.split('\\')) for path in paths]
                bottom_paths = []
                top_paths = []
                for path_tup in path_tups:
                    # 判断当前路径是否为底层目录
                    is_bottom = True
                    for other_tup in path_tups:
                        # 判断当前路径是否是其他路径的上级目录
                        if path_tup != other_tup and path_tup[:len(other_tup)] == other_tup:
                            is_bottom = False
                            break
                    # 如果当前路径是底层目录，则加入到结果列表中
                    if is_bottom:
                        bottom_paths.append('\\'.join(path_tup))
                    else:
                        top_paths.append('\\'.join(path_tup))
                return [bottom_paths,top_paths]
            moves_ancestors = find_bottom_top_paths(_imports_dir)[0]
            for i_ac in moves_ancestors:
                i_ds = HWAQL.find_object_descendants_except(i_ac,except_object_type="AudioFileSource")
                for i_d in i_ds:
                    if i_d['path'] not in _imports_dir and i_d['path'] not in _descendants_not_pair:
                        if not checkSound and i_d['type'] == 'Sound':
                            continue
                        _descendants_not_pair.append(i_d['id'])

        if len(not_imports_dir) > 0:
            print('--------------------------------------------')
            print("WARNING:以下文件夹找不到对应的SoundObject，可能之前没导入进工程内")
            for i in not_imports_dir:
                print(i)
        if len(_descendants_not_pair) > 0:
            print('--------------------------------------------')
            print("WARNING:以下所对应的重命名/移动对象的container的子中集含有不与文件夹关联的Object")
            p = r"$"
            for irfrc in _descendants_not_pair:
                p = p + "\"%s\","%(irfrc)
            p = p.rsplit(",",1)[0]
            print(p)
            print("请将字符串复制到wwise的搜索栏中进行查看")

        if len(data['Hwaapi'][0]) > 0:
            for i_rename in data['Hwaapi'][0]:
                if i_rename['object'] in _imports_dir:
                    AK_API.object_setName(i_rename)
        else:
            for i_a_m in data['Hwaapi'][1]:
                if i_a_m['object'] in moves_ancestors:
                    AK_API.object_move(i_a_m)
        return data
    def waapi_both_moved(data):
        #方案一：
        #SoundObject会因为文件夹移动导致爆红，我们在移动前重新导入他们即可。
        #然后音频不需要管，只需要检测要移动的文件夹内的音频是否在对应的路径。
        #检测移动/重命名的文件夹的原路径是否对应在工程中有相应的路径
        #检测移动/重命名的文件对应的containerObject是否含有其他东西
        #检测完后打印警示，如果只是重命名的，重命名其文件夹
        #如果是移动的，检测拿出其最父层级，只要移动这些就好了
        not_imports_wav = []#没有导入的
        others_imports_rfrcs = []#音频路径及其被引用的所有SoundObject
        true_move_rename = []
        Rename_Move_ornot = True
        if 'value' in data['Hwaapi'][1][0].keys():
            Rename_Move_ornot = True
        elif 'parent' in data['Hwaapi'][1][0].keys():
            Rename_Move_ornot = False
        _imports = []
        for i_p in data['Hwaapi'][1]:#rename以及move的导入爆红。
            fpth_old = data['Actions']['monitor_path']+"\\"+data['Actions']['language']+i_p['object'].split(r"\Actor-Mixer Hierarchy\Default Work Unit",1)[1]+".wav"
            if Rename_Move_ornot:
                fpth_new = data['Actions']['monitor_path']+"\\"+data['Actions']['language']+i_p['object'].split(r"\Actor-Mixer Hierarchy\Default Work Unit",1)[1].rsplit("\\",1)[0]+"\\"+i_p['value']+".wav"
            else:
                fpth_new = data['Actions']['monitor_path']+"\\"+data['Actions']['language']+i_p['parent'].split(r"\Actor-Mixer Hierarchy\Default Work Unit",1)[1]+"\\"+fpth_old.rsplit("\\",1)[1]
            i_p_rfrc = HWAQL.find_wav_referencesTo(fpth_old)
            if len(i_p_rfrc) < 1:
                not_imports_wav.append(fpth_old)
            else:
                others_rfrc = []
                for rfrc in i_p_rfrc:
                    audiosources = HWAQL.find_object_children(rfrc['id'])
                    for i_a in audiosources:
                        AK_API.object_delete({'object':i_a['id']})
                    _imports.append(
                        {
                            'audioFile':fpth_new,
                            'objectPath':rfrc['path'],
                            'objectType':'AudioFileSource',
                        }
                    )
                    if rfrc['path'] != i_p['object']:
                        others_rfrc.append(rfrc)
                    else:
                        true_move_rename.append(i_p)
                if len(others_rfrc) > 0:
                    t = []
                    t.append(fpth_old+'-'+fpth_new)
                    t.append(others_rfrc)
                    others_imports_rfrcs.append(t)
        import_args = {
            "importOperation": "useExisting",  # 创建新的对象；若存在同名的现有对象，则将现有对象销毁。
            "default": {
                "importLanguage": data['Actions']['language'],
                "importLocation":r"\Actor-Mixer Hierarchy\Default Work Unit",
                },
            "imports":_imports
        }
        AK_API.audio_import(import_args)
        if len(not_imports_wav) > 0:
            print('--------------------------------------------')
            print("WARNING:以下移动/重命名的文件夹内的音频找不到对应的SoundObject，可能之前没导入进工程内")
            for i in not_imports_wav:
                print(i)
        if len(others_imports_rfrcs) > 0:
            print('--------------------------------------------')
            print("WARNING:以下SoundObject路径与音频路径不对应，这些是引用了已删除音频的SoundObject")
            for irfrc in others_imports_rfrcs:
                p = irfrc[0]+r":$"
                for objpth in irfrc[1]:
                    p = p + "\"%s\","%(objpth['id'])
                p = p.rsplit(",",1)[0]
                print(p)
            print("以上是音频以及引用音频的SoundObject，请将音频路径冒号后面的字符串复制到wwise的搜索栏中进行查看")
        dt = data
        dt['Hwaapi']  = dt['Hwaapi'][0]
        HWAAPI.waapi_dirs_moved(dt,False)
        return data

class DirMonitor(object):
    """文件夹监视类，将得到的操作数据发送到Transfer.Act中"""
    
    def __init__(self, aim_path):
        """构造函数，需要监控路径"""
        self.aim_path= aim_path
        DirMonitor.Aim_Path = self.aim_path
        self.observer = Observer()

    Aim_Path = ""

    def start(self):
        """启动监视"""
        event_handler = FileEventHandler(self.aim_path)
        self.observer.schedule(event_handler, self.aim_path, True)
        self.observer.start()

    def join(self):
        self.observer.join()

    def stop(self):
        """停止监视"""
        self.observer.stop()

layout = [
    [sg.B('Wwise_Connect')],
    [sg.B('Wwise_Disconnect')]
    ]
window = sg.Window('TestTest', layout, keep_on_top=True)

def gc():
    if AK_API.hwaapi.waapi_isconnect_ornot() == None:
        print("ERROR:未与Wwise连接,请打开Wwise工程")
        print("--------------------------------------------")
    print("现在请在控制台中输入您的Wwise工程音频源文件夹路径并按回车键")
    print(r"例如C:\Users\Desktop\Civ6WwiseTest\Originals")
    s = input()
    if s == '作者':
        print("黄里的小壳")
        print("WTOOLSv1_Beta")
        return gc()
    elif s[-len(r"\Originals"):] == r'\Originals':
        return s
    else:
        return gc()

def connect_(bool:bool):
    print('--------------------------------------------')
    if bool:
        if not AK_API.hwaapi.waapi_isconnect_ornot():
            AK_API.hwaapi.waapi_connect()
            sg.popup_ok('Done!',keep_on_top=True)
            if not HWAAPI.AutoImport:
                HWAAPI.AutoImport = True
                Transfer().loop_transfer.start()
                HWAAPI().loop_akimport.start()
        else:
            print("已连接!")
            sg.popup_ok('已连接!',keep_on_top=True)

    else:
        if AK_API.hwaapi.waapi_isconnect_ornot():
            AK_API.hwaapi.waapi_disconnect()
            HWAAPI.AutoImport = False
            Transfer.Act = Queue()
            Transfer.Act.queue.clear()
            Transfer.Act = Queue()
            Transfer.Act.queue.clear()
            HWAAPI.Import = Queue()
            HWAAPI.Import.queue.clear()
            HWAAPI.WwiseReturns = Queue()
            HWAAPI.WwiseReturns.queue.clear()
            sg.popup_ok('Done!',keep_on_top=True)
        else:
            print('已断开!')
            sg.popup_ok('已断开!',keep_on_top=True)


print("WTOOLSv1_beta该版本的导入工具以通过监控工程文件夹的路径")
print("在文件夹内的移入(添加)、移除(删除)、移动音频wav文件或者文件夹操作")
print("可以实时进行音频的导入，删除以及工程内层级的移动、这些都是相对应的")
print("如果有些文件或object不与这些操作有关联的话会自动进行打印提示。")
print("启动该工具前先打开工程，如果单独打开会连接工程失败。")
print("")
print("版本说明：")
print("1:")
print("目前在文件夹内进行添加文件夹，仅支持对应创建Actor-Mixer的Container层级。")
print("后续可根据文件夹名字或其他定义来创建相应的container")
print("也可以直接在工程内先创建与文件夹名字相同的、路径相同的各种类型的Container再进行导入")
print("或者使用容器转换工具来进行替换，这些都可以达到让文件夹与Container保持名字相同")
print("2:")
print("目前文件夹中语言的语音部分不建议拖动或者删除，会直接删除")
print("后续会进行优化，删除只删除对应语言")
print("目前文件夹路径与工程路径是绝对同步的，所以各项目有不便的地方")
print("后续会进行优化，可以进行自定义工程路径与文件夹路径的对应")
print(r"如文件夹E:\WwisePJ\Originals\SFX\System")
print("对应↓")
print(r"工程路径\Actor-Mixer Hierarchy\Default Work Unit\Common\System")
print("")
print("按钮使用说明：")
print("Wwise_Connect:进行与Wwise工程的本地连接，开启同步操作功能")
print("Wwise_Disconnect:断开连接，关闭同步操作功能")
print("--------------------------------------------")

if __name__ == "__main__":
    #s = r"E:\UnityPj\TestWwise\My project1\Assets\Wwise\WwisePJ\Originals"
    s = gc()
    monitor = DirMonitor(s)
    monitor.start()
    Transfer().loop_transfer.start()
    HWAAPI().loop_akimport.start()
    while True:
        event,values = window.read()
        if event is None:
            break
        if event == 'Wwise_Connect':
            window['Wwise_Connect'].update(disabled=True)
            #HWAAPI.AKIMPORT_TEST()
            connect_(True)
            window['Wwise_Connect'].update(disabled=False)

        if event == 'Wwise_Disconnect':
            window['Wwise_Disconnect'].update(disabled=True)
            connect_(False)
            window['Wwise_Disconnect'].update(disabled=False)

    HWAAPI.AutoImport = False
    AK_API.hwaapi.waapi_disconnect()