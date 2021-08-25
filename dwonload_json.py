#--------------------------------脚本不想重构就这么运行就好--------------------------------
#定时下载最新的地块json数据
import uuid
import datetime
from requests.auth import HTTPDigestAuth
import zipfile
import ee 
import os
import shutil
import requests
import time
import json
import wmi
import sys
import logging
from app_r_ import to_png

# 引入 http.client
import http.client

def getNDVI(image):
    return image.normalizedDifference(['B8', 'B4']).rename("NDVI")

def DnsDef():
    wmiService = wmi.WMI()
    colNicConfigs = wmiService.Win32_NetworkAdapterConfiguration(IPEnabled=True)
    if len(colNicConfigs) < 1:
        print("没有找到可用的网络适配器")
        exit()
    objNicConfig = colNicConfigs[0]
    arrDNSServers = ['114.114.114.114']
    returnValue = objNicConfig.SetDNSServerSearchOrder(DNSServerSearchOrder=arrDNSServers)
    if returnValue[0] == 0:
        print("修改成功")
    else:
        print("修改失败")

def mymovefile(srcfile,dstfile):
    if not os.path.isfile(srcfile):
        print("{} not exist!".format(srcfile))
    else:
        fpath,fname=os.path.split(srcfile)    #分离文件名和路径
        if not os.path.exists(dstfile):
            os.makedirs(dstfile)               #创建路径
        dstfile = os.path.join(dstfile, fname)
        shutil.move(srcfile,dstfile)          #移动文件
        print("move %s -> %s"%(srcfile,dstfile))

#修改dns
# DnsDef()
# formdata = {
#     "userName": "admin",
#     "passWord": "666666"
# }
dwonurl= r"http://112.126.102.26:8083/v1/field/exportFieldList"
upurl = r"http://112.126.102.26:8083/v1/framarea/add"
dir_all = (datetime.datetime.now() - datetime.timedelta(days=3)).strftime("%Y-%m-%d")
print(dir_all)
#按平台数据的时间创建workspace
path = "E:\\项目支持\\gee\\data\\" + dir_all
if not os.path.exists(path):
    os.makedirs(path)
path_zip = path + "\\zip\\"
if not os.path.exists(path_zip):
    os.makedirs(path_zip)
path_tiff = path + "\\TIFF\\"
if not os.path.exists(path_tiff):
    os.makedirs(path_tiff)
png_path = path + "\\png\\"
png_bf = path + "\\png_bf\\"
if not os.path.exists(png_bf):
    os.makedirs(png_bf)

headers = {
    "Authorization": "2"
}

#设置log日志
logging.basicConfig(
        level=logging.DEBUG,#控制台打印的日志级别,debug，info，warning，error等几个级别
        filename=path + 'new.log',
        filemode='w',
        format=
        '%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s') #记录时间，文件位置，级别等信息

#下载地块json
response = requests.get(dwonurl, headers=headers)
pathj = path + "\\" + "FieldList.json"
fileObject = open(pathj, 'w', encoding='utf8')
fileObject.write(response.text) 
fileObject.close()

#下载时间区间
startDate_all = (datetime.datetime.now() - datetime.timedelta(days=3)).strftime("%Y-%m-%d")
endDate_all = (datetime.datetime.now() - datetime.timedelta(days=2)).strftime("%Y-%m-%d")

#读取平台geojson数据
Geodata = pathj
f =  open(Geodata, encoding='utf-8')
res = f.read()
geoms = json.loads(res)  # 解析string格式的geojson数据
f.close
fc = geoms["features"]

#下载GEE地块数据
try:
    # update the proxy settings
    # os.environ['HTTP_PROXY'] = 'http://127.0.0.1:8081'
    # os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:8081'
    ee.Initialize()
    img_col = ee.ImageCollection('COPERNICUS/S2_SR')
    #---------------批量处理平台已有的地块遥感数据---------------
    for f in fc:
        region = f['geometry']['coordinates'][0]
        feat = ee.Geometry.Polygon(f["geometry"]['coordinates'])
        dis = f.get('properties').get("prop0")
        try:
            img = ee.Image(img_col.filterBounds(feat).filterDate(startDate_all, endDate_all).mosaic())
            ndvi = getNDVI(img)
            img = ndvi.clip(feat.buffer(20)).reproject('EPSG:4326',None,10)
            url = img.getDownloadURL({
                'name':dir_all + "_" + str(dis) +"_3",
                'crs': 'EPSG:4326',
                'region':feat,
                'scale': 10
            })
            print("{}-url:{}\n".format(dis, url))
            pathzf = path_zip + "\\" + str(dis) + ".zip"
            r = requests.get(url)
            try:
                with open(pathzf, "wb") as code:
                    code.write(r.content)
            except Exception as e:
                print(str(e))
            #图片解压缩
            #--------解压下载的zip到指定文件-----------
            zip_file = zipfile.ZipFile(pathzf)
            zip_list = zip_file.namelist() # 得到压缩包里所有文件
            for f in zip_list:
                zip_file.extract(f, path_tiff) # 循环解压文件到指定目录
            zip_file.close() # 关闭文件，必须有，释放内存
        except Exception as e:
            print(str(e))
except:
    # print("代理问题，链接不到google")
    logging.critical("代理问题，链接不到google")

#TIFF重命名
filename_list = os.listdir(path_tiff)
for i in filename_list:
    if i.endswith(".tif"):
        used_name = path_tiff + "\\"+ i
        new_name = path_tiff + "\\"+ i.split("_")[1] + "_3.tif"
        try:
            os.rename(used_name, new_name)
        except WindowsError: 
            os.remove(new_name) 
            os.rename(used_name, new_name)
    else:
        print("此文件非tif格式！")

#图片出图
to_png(pathj)

#删除代理
# del os.environ['HTTP_PROXY']
# del os.environ['HTTPS_PROXY']
#修改dns
# DnsDef()
# 配置如下
http.client.HTTPConnection._http_vsn = 10
http.client.HTTPConnection._http_vsn_str = 'HTTP/1.0'
#上传png图片
for root, dirs, files in os.walk(png_path):
    for file in files:
        if file.endswith(".png"):
            Fpath = os.path.join(root, file)#后期循环获取变量
            uid = str(uuid.uuid4())
            filename = "{}_{}".format(uid, file)
            time_up = dir_all
            print("日期{}---文件{}".format(time_up, filename))
            formdata = {
                "date": time_up,
            }
            files = {
                "files": (filename, open(Fpath,"rb"), "image/png")
            }
            try:
                response = requests.post(upurl, headers=headers, data=formdata, files=files, stream=True)
                print(response.text)
                if response.content == "500":
                    mymovefile(file,png_bf)
                logging.debug("file{} is {}".format(file, response.text))
            except requests.exceptions.RequestException as e:
                print(e)
                print('失败')
                mymovefile(file,png_bf)
                logging.debug("file{} is {}".format(file, e))
        time.sleep(2)


