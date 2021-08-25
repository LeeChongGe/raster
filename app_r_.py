from cilpRaster import Clip, proj, clipR, fourpiont
from colorbar import ishow
from resample import ReprojectImages
import sys, os, json, time, shutil
import shapefile, rasterio

def to_png(shpp):
    print("-------start--------")
    Tpath = shpp.split("\\")[:-1]
    TIFFpath = "\\".join(Tpath) + "\\TIFF"
    reprojectpath = "\\".join(Tpath) + "\\reproject"
    r_clip_path = "\\".join(Tpath) + "\\r_clip"
    jsonpath = "\\".join(Tpath) + "\\json"
    png_path = "\\".join(Tpath) + "\\png"
    if not os.path.exists(TIFFpath):
        os.makedirs(TIFFpath)
    if not os.path.exists(reprojectpath):
        os.makedirs(reprojectpath)
    if not os.path.exists(r_clip_path):
        os.makedirs(r_clip_path)
    if not os.path.exists(jsonpath):
        os.makedirs(jsonpath)
    if not os.path.exists(png_path):
        os.makedirs(png_path)
    #打开json矢量
    f =  open(shpp, encoding='utf-8')
    res = f.read()
    geoms = json.loads(res)  # 解析string格式的geojson数据
    f.close
    #四点坐标
    fourpiont(shpp)
    # 重采样
    for i in os.listdir(TIFFpath):
        if i.endswith('.tif'):
            ii = i.split('.')[0] + '_reproject.tif'
            outputfilePath = os.path.join(reprojectpath, ii)
            inputfilePath = os.path.join(TIFFpath, i)
            ReprojectImages(outputfilePath, inputfilePath)

    #裁剪重采样
    print("--------裁剪重采样---------")
    for r in os.listdir(reprojectpath):
        for i in range(len(geoms['features'])):
            nname = geoms['features'][i]['properties']['prop0']
            if r.split('.')[-1] == "tif" and str(r.split("_")[0]) == str(nname):
                geo = [geoms['features'][i]['geometry']]
                newtiffname = r_clip_path + "\\" + str(nname) + "_r_clip.tif"
                raaa = os.path.join(reprojectpath, r)
                clipRn = clipR(raaa, geo, newtiffname)
                print("------clip over--------")

                if clipRn is None:
                    print("{} clipr {} lose!".format(nname, r))    
                else:
                    print("{} clipr {} win!".format(nname, r))

    #出图
    for i in os.listdir(r_clip_path):
        if i.endswith('.tif'):
            inputoPath = os.path.join(r_clip_path, i)
            # ii = i.split('.')[0] + '.png'
            # outputPath = os.path.join(png_path, ii)
            # ishow(inputoPath, outputPath)
            ishow(inputoPath, png_path)
        
            # ndviMean = ishow(inputoPath)
            # nname = i.split("_")[0]
            # #添加ndvi平均值
            # xypath = str(nname) + ".json"
            # xypath = os.path.join(jsonpath, xypath)
            # with open(xypath,"r",encoding='utf-8') as e:
            #     strf = e.read()
            #     a = json.loads(strf)
            # a["meanNdvi"] = str(ndviMean)
            # with open(xypath, "w+") as e:
            #     json.dump(a, e, ensure_ascii=False)

    # 抠图
    # for i in os.listdir(shp):
    #     if i.endswith('.png'):
    #         i = os.path.join(shp, i )
    #         transparent_background(i)
    return png_path
if __name__=='__main__':
    shpp = r'E:\项目支持\gee\data\2021-05-09\FieldList.json'
 
    to_png(shpp)


