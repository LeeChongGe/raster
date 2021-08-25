from osgeo import gdal
from osgeo import gdal_array
from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt
from matplotlib import cm, colors
import matplotlib
import numpy as np
import numpy.ma as ma 
import rasterio
import pyproj
import math

def generateCmap(breakPointColors, breakPoints=None, sensitivity=256, 
               name="userCmap"):
    '''
    Aimed at generate user customized ListedColormap instance, to be used when 
    plotting with matplotlib.
    Arguments:
    ----------
    breakPointColors: 
        An array of color difinitions. Can be "rgba" vector or a string (like 
        "red") that `matplotlib.colors.to_rgba()` accepts.
    breakPoints: 
        Optional. An array of numbers that defines the border of color 
        gradients. The values does not necessarily match the border of the 
        data to plot, but will be reflected as ratio on the plot. Must be of 
        the same length as `breakPointColors`.
    sensitivity: 
        An integer for how many intrinsic intervals in the colormap. Default 
        `256`. Should use larger value if there are breakpoints close to each 
        other.
    Return:
    ----------
        a matplotlib.colors.ListedColormap object, that can be used for "cmap"
    argument in matplotlib plotting function.
    Example:
    ----------
    >>> import matplotlib.pyplot as plt
    >>> cmap = generateCmap(['blue', 'white', 'red'])
    >>> plt.scatter(range(100), range(100), c=range(100), cmap=cmap)
    '''
    # Input Check
    assert len(breakPointColors) >= 2
    if breakPoints != None:
        assert len(breakPoints) == len(breakPointColors)
        assert len(set(breakPoints)) == len(breakPoints), \
               "Should not give duplicated value in 'breakPoints'"
    else:
        breakPoints = list(range(len(breakPointColors)))
    
    breakPointColors = np.array(breakPointColors)
    assert len(breakPointColors.shape) == 1 or \
           len(breakPointColors.shape) == 2
    if len(breakPointColors.shape) == 1:
        assert str(breakPointColors.dtype).startswith('<U'), \
               "Color specification dtype not understandable"
    elif len(breakPointColors.shape) == 2:
        assert breakPointColors.shape[1] in [3, 4] and \
               breakPointColors.dtype in ['int32', 'float64'], \
               "'rgb(a)' color specification not understandable."

    ## Randomly fetch an ListedColormap object, and modify the colors inside
    cmap = cm.get_cmap("viridis", sensitivity)
    cmap.name = name
    
    # Format the input
    minBP, maxBP = min(breakPoints), max(breakPoints)
    scaledBP = [round((i-minBP)/(maxBP-minBP)*(sensitivity-1)) \
                for i in breakPoints]
    assert len(set(scaledBP)) == len(breakPoints), \
           "Sensitivity too low"
    sortedBP = sorted(scaledBP)
    sortedBPC = []
    for i in sortedBP:
        idx = scaledBP.index(i)
        sortedBPC.append(breakPointColors[idx])
    BPC_rgba = np.array([colors.to_rgba(i) for i in sortedBPC])
    # Now replace colors in the Colormap object
    for i in range(1, len(sortedBP)):
        ## Indices when slicing colormap.colors
        start = sortedBP[i-1]
        end = sortedBP[i] + 1
        n = end - start
        ## Color range
        startC = BPC_rgba[i-1]
        endC = BPC_rgba[i]
        for i in range(3):
            cmap.colors[start:end, i] = np.linspace(startC[i], endC[i], n)
        
    return cmap

# 读取tif影像函数            
def readTifAsArray(tifPath):
    dataset = gdal.Open(tifPath, gdal.GA_ReadOnly)     
    if dataset == None:
        print(tifPath + "文件错误")
        return tifPath
            
    image_datatype = dataset.GetRasterBand(1).DataType  
    row = dataset.RasterYSize
    col = dataset.RasterXSize
    nb  = dataset.RasterCount
    proj = dataset.GetProjection()
    gt = dataset.GetGeoTransform()
    
    if nb != 1:
        print("波段不唯一")
        array = np.zeros((row, col, nb), 
                        dtype = gdal_array.GDALTypeCodeToNumericTypeCode(
                                image_datatype))
        for b in range(nb):
            band = dataset.GetRasterBand(b + 1)
            nan = band.GetNoDataValue()
            array[:, :, b] = band.ReadAsArray()
    else:
        print("波段唯一")
        array = np.zeros((row,col),
                         dtype = gdal_array.GDALTypeCodeToNumericTypeCode(
                         image_datatype))
        band = dataset.GetRasterBand(1)        
        nan = band.GetNoDataValue()        
        array = band.ReadAsArray()
    del dataset
    # print(array)
    return array, nan, gt, proj, nb

def ishow(file, png_path):
    data  = readTifAsArray(file)[0] # 栅格数组
    affine = readTifAsArray(file)[2] # 读取仿射变换参数
    width = data.shape[1] 
    height = data.shape[0]

    vmin = data.min()
    vmax = data.max()

    map_width = width * affine[1] # 影像的宽度米
    map_height = height * affine[1] # 高度 米
    xmin = affine[0] # 分别为左下xy 右上xy坐标
    xmax = xmin + map_width
    ymax = affine[3]
    ymin = ymax - map_height
    extent = [xmin, xmax, ymin, ymax] # [left, right, bottom, top]
    print(extent)
    m = Basemap(llcrnrlon=xmin, llcrnrlat=ymin, urcrnrlon=xmax, urcrnrlat=ymax, # 左下右上经纬度坐标 关键在于如何将已投影的坐标转换为经纬度坐标
                # projection='aea', # albers等面积投影
                epsg = 4326,
                resolution='h', lat_0=0, lon_0=105, lat_1=25, lat_2=47) # 指定albers的参考纬度线和中心经度线
                # There might be other parameters to set depending on your CRS


    if readTifAsArray(file)[4] == 1:
        ndv = -3.40282306e+38
        # ndv = 0
        data[data <= ndv] = np.nan # 去除nodata
        ndviMean = np.mean(data)
        # masked_data = ma.masked_where(data == ndv, data)
        # norm = matplotlib.colors.Normalize(vmin=vmin, vmax=vmax)
        norm = matplotlib.colors.Normalize(vmin=0, vmax=1)
        cmap1 = generateCmap(['Firebrick', 'Yellow', 'Green', 'MidnightBlue'],[0,2,3,5])
        m.imshow(data, origin='upper', extent=extent, cmap=cmap1, norm=norm) # 绘制栅格数据
    else:
        m.imshow(data, extent=extent) # 绘制栅格数据
    name = file.split("\\")[-1]
    nam = name.split("_")[0] + '_3.png'
    pngg = png_path + "\\" + nam
    print(pngg)
    plt.axis('off')
    plt.savefig(pngg, dpi=500, transparent=True,bbox_inches='tight',pad_inches = 0) # , transparent=True透明保存
    #关闭很关键，不然会出现图片叠加的情况
    plt.close()
    # return ndviMean
if __name__ == "__main__":
    file = r"V:\data2\shp\r_clip\1302_r_clip.tif"
    ishow(file)
    