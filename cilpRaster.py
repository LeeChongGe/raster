import operator
from osgeo import gdal, gdal_array, osr
import shapefile, rasterio
import sys, os, json, time, shutil
from PIL import Image
import numpy as np
from rasterio import crs

from rasterio.mask import mask
from rasterio.warp import reproject, Resampling, transform_bounds, calculate_default_transform as calcdt
from rasterio.windows import get_data_window
# from tif16to8 import compress
from colorbar import ishow

#投影变换
def proj(Tiff, pojtiff, dst_crs = 'EPSG:4326'):
    # pathDir, pathTiff = os.path.split(Tiff)
    # wgspath = os.path.join(pathDir, "WGS84")
    # if not os.path.exists(wgspath):
    #     os.makedirs(wgspath)
    # #pojtiff = Tiff.split(".")[0] + "_.tif" 
    # pojtiff = pathDir + "\\WGS84\\" + pathTiff
    #转为地理坐标系wgs84
    print("-----proj start------")
    #dst_crs = 'EPSG:4326'
    with rasterio.open(Tiff) as src_ds:
        #数据集的元数据信息
        profile = src_ds.meta.copy()
        #计算在新空间参考系下的仿射变换参数，图像尺寸
        dst_transform, dst_width, dst_height = calcdt( src_ds.crs, dst_crs, src_ds.width, src_ds.height, *src_ds.bounds)
        #更新数据集的元数据信息
        profile.update({
            'crs': dst_crs,
            'transform': dst_transform,
            'width': dst_width,
            'height': dst_height,
            'nodata': 0
        })

        #重投影并写入数据
        with rasterio.open(pojtiff, 'w', **profile) as dst_ds:
            for i in range(1, src_ds.count + 1):
                reproject(
                    # 源文件参数
                    source=rasterio.band(src_ds, i),
                    src_crs=src_ds.crs,
                    src_transform=src_ds.transform,
                    # 目标文件参数
                    destination=rasterio.band(dst_ds, i),
                    dst_transform=dst_transform,
                    dst_crs=dst_crs,
                    # 其它配置
                    resampling=Resampling.nearest,
                    num_threads=2)
    print("-----proj over------")
    # return wgspath

#geojson裁剪栅格
def Clip(Tiff, Geodata, name=None):
    print("------clip start--------")
    #打开json矢量
    f =  open(Geodata, encoding='utf-8')
    res = f.read()
    geoms = json.loads(res)  # 解析string格式的geojson数据
    f.close
    print(len(geoms['features']))
    for i in range(len(geoms['features'])):
        geo = [geoms['features'][i]['geometry']]
        nname = geoms['features'][i]['properties']['prop0']
        pathlist = Geodata.split("\\")[:-1]
        newtiffname = "\\".join(pathlist) + "\\TIFF\\" + str(nname) + ".tif"

        clipRn = clipR(Tiff, geo, newtiffname)
        print("------clip over--------")

        if clipRn is None:
            print("{} clip {} lose!".format(nname, Tiff))
            return None, None    
        else:
            print("{} clip {} win!".format(nname, Tiff))
            return newtiffname, nname
            print("--------wwww------------")
            # #将16位遥感图像压缩至8位，并保持色彩一致
            # src = rasterio.open(newtiffname)
            # if src.dtypes[0] != "uint8":
            #     compress(newtiffname, newtiffname_8)
            #     print("8位转换成果")
            #     #图片格式转换，转成png格式
            #     while True:
            #         if os.path.exists(newtiffname_8):
            #             tif2png(newtiffname_8)
            #             break
            # else:
            #     #图片格式转换，转成png格式
            #     while True:
            #         if os.path.exists(newtiffname):
            #             tif2png(newtiffname)
            #             break  
            

def fourpiont(Geodata):
    lt = []
    ls = []
    #创建地块四点坐标
    #打开json矢量
    f =  open(Geodata, encoding='utf-8')
    res = f.read()
    geoms = json.loads(res)  # 解析string格式的geojson数据

    for i in range(len(geoms['features'])):
        geo = [geoms['features'][i]['geometry']]
        nname = geoms['features'][i]['properties']['prop0']
        #print("{}--{}".format(nname, geo))
        pathlist = Geodata.split("\\")[:-1]
        xypath = "\\".join(pathlist) + "\\json\\" + str(nname) + ".json"
        #获取四至坐标,比较坐标的最大最小值
        nb = geo[0]['coordinates'][0]
        for j in range(len(nb)):
            lt.append(nb[j][0])
            ls.append(nb[j][1])
        minX = sorted(lt)[-1]
        maxX = sorted(lt)[0]
        minY = sorted(ls)[-1]
        maxY = sorted(ls)[0]
        xy = {"minX":minX, "maxX":maxX, "minY":minY, "maxY":maxY}
        #输出四至坐标text
        with open(xypath,"w") as e:
            json.dump(xy, e)
        # print("四点坐标完成！")

def clipR(tiff, geo, newtiffname):
    # 掩模得到相交区域
    out_image = None
    #打开影像
    rasterfile = tiff
    with rasterio.open(rasterfile) as src:
        print(src.nodata)
        try:
            out_image, out_transform = mask(src, geo, all_touched=True, crop=True, nodata=-3.40282306e+38)
            # print('out_image:{},out_transform:{}'.format(out_image, out_transform))
        except Exception as e:
            print("掩膜错误{}".format(e))
        print("------clipr--------")
        boo = not np.any(np.nan_to_num(out_image))
        bo = out_image is None
        if boo or bo:
            return None
        out_meta = src.meta.copy()
        out_meta.update({"driver": "GTiff",
                        "height": out_image.shape[1],
                        "width": out_image.shape[2],
                        "transform": out_transform,
                        "crs":src.crs})
        
        band_mask = rasterio.open(newtiffname, "w", **out_meta)
        band_mask.write(out_image)
        return out_image
        



#获取文件大小
def get_size(file):
    # 获取文件大小:KB
    size = os.path.getsize(file)
    return size / 1024

#拼接输出文件地址
def get_outfile(infile, outfile):
    if outfile:
        return outfile
    dir, suffix = os.path.splitext(infile)
    outfile = '{}_3{}'.format(dir, suffix)
    return outfile

#压缩文件到指定大小
def compress_image(infile, outfile='', mb=1500, step=10, quality=80):
    """不改变图片尺寸压缩到指定大小
    :param infile: 压缩源文件
    :param outfile: 压缩文件保存地址
    :param mb: 压缩目标，KB
    :param step: 每次调整的压缩比率
    :param quality: 初始压缩比率
    :return: 压缩文件地址，压缩文件大小
    """
    o_size = get_size(infile)
    if o_size <= mb:
        return infile
    outfile = get_outfile(infile, outfile)
    while o_size > mb:
        im = Image.open(outfile)
        im.save(outfile, quality=quality)
        if quality - step < 0:
            break
        quality -= step
        o_size = get_size(outfile)
    #return outfile, get_size(outfile)

#修改文件到指定大小
def resize_image(infile, outfile='', mb=3000, x_s=2048):
    """修改图片尺寸
    :param infile: 图片源文件
    :param outfile: 重设尺寸文件保存地址
    :param x_s: 设置的宽度
    :return:
    """
    o_size = get_size(infile)
    if o_size <= mb:
        outfile = get_outfile(infile, outfile)
        shutil.copyfile(infile, outfile)
    else:
        im = Image.open(infile)
        x, y = im.size
        y_s = int(y * x_s / x)
        out = im.resize((x_s, y_s), Image.ANTIALIAS)
        outfile = get_outfile(infile, outfile)
        out.save(outfile)

#tif转png
def tif2png(output_raster):
    ds=gdal.Open(output_raster)
    output_png = output_raster.split(".")[0] + ".png"
    driver=gdal.GetDriverByName('PNG')
    dst_ds = driver.CreateCopy(output_png, ds)
    dst_ds = None
    ds = None
    print("------tif2png--------")
    #图片压缩，对png格式进行压缩
    while True:
        if os.path.exists(output_png):
            resize_image(output_png)
            #compress_image(output_png)
            break


#抠图
def transparent_background(path):
    try:
        img = Image.open(path)
        print(img)
        img = img.convert("RGBA")  # 转换获取信息
        pixdata = img.load()
        # color_no = get_convert_middle(path) + 30  # 抠图的容错值
        color_no = 30

        for y in range(img.size[1]):
            for x in range(img.size[0]):
                # if pixdata[x, y][0] > color_no and pixdata[x, y][1] > color_no and pixdata[x, y][2] > color_no and pixdata[x, y][3] > color_no:
                if pixdata[x, y][0] < color_no and pixdata[x, y][1] < color_no and pixdata[x, y][2] < color_no and pixdata[x, y][3] == 255:
                    pixdata[x, y] = (255, 255, 255, 0)

        if not path.endswith('png'):
            os.remove(path)
            replace_path_list = path.split('.')
            replace_path_list = replace_path_list[:-1]
            path = '.'.join(replace_path_list) + '.png'

        img.save(path)
        print("-----{} over-----".format(path))
        img.close()
    except Exception as e:
        print("-----{} lose-----".format(path))
        return False
    return path


if __name__ == "__main__":
    ra = input("需要裁剪的影像:")
    shp = input("用来裁剪的矢量:")
    print("-------start--------")

    # # 重投影wgs84
    # wgspath = os.path.join(ra, "WGS84")
    # if not os.path.exists(wgspath):
    #     os.makedirs(wgspath)
    
    # for r in os.listdir(ra):
    #     pojtiff = ra + "\\WGS84\\" + r
    #     r = os.path.join(ra, r)
    #     print(r)
    #     rasterdata = rasterio.open(r)
    #     if rasterdata.crs['init'] != "epsg:4326":
    #         proj(r, pojtiff)
    #     else:
    #         shutil.copyfile(r, pojtiff)

    # 裁剪栅格
    for sh in os.listdir(shp):
        for r in os.listdir(ra):
            if sh.split(".")[-1] == "json" and r.split(".")[-1] == "tif":
                print("---------1-----------")
                shpp = os.path.join(shp, sh)
                raa = os.path.join(ra, r)
                Clip(raa, shpp)
    # 抠图
    # for i in os.listdir(shp):
    #     if i.endswith('.png'):
    #         i = os.path.join(shp, i )
    #         transparent_background(i)



                

