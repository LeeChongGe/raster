#!/usr/bin/env python3.7
# encoding: utf-8
"""
  @author: ISR
  @contact: 84692429@qq.com
  @file:
  @time:
  @desc:
  mtx，相机内参；dist，畸变系数；
"""

import cv2
import numpy as np
from pyexiv2 import Image
import piexif
from scipy import misc

def image_info(imagepath):

    """获取xmp、xeif信息"""

    img = Image(imagepath)
    exif = img.read_exif()  # 读取 EXIF 元数据，这会返回一个字典
    #exifdata = piexif.load(imagepath)
    img.read_iptc()
    xmp = img.read_xmp()
    #b_name = xmp['Xmp.drone-dji.BandName']
    img.close()  # 操作完之后，记得关闭图片

    return xmp, exif

def image_mat(xmp):

    """根据xmp获取影像内方位元素和畸变系数"""

    # 内方位元素和畸变校正参数 calibrate_date,fx,fy,cx,cy,k1,k2,p1,p2,k3
    clibrate_data = xmp['Xmp.drone-dji.DewarpData']
    clibrate_data = clibrate_data.split(";")[1].split(",")

    # 内参
    fx = float(clibrate_data[0])
    fy = float(clibrate_data[1])
    cX = float(clibrate_data[2])
    cY = float(clibrate_data[3])

    # 内参矩阵
    cam_mat = np.zeros((3, 3))
    cam_mat[0, 0] = fx
    cam_mat[1, 1] = fy
    cam_mat[2, 2] = 1.0
    cam_mat[0, 2] = cX
    cam_mat[1, 2] = cY
    # print(cam_mat)

    # 畸变系数
    k1 = float(clibrate_data[4])
    k2 = float(clibrate_data[5])
    p1 = float(clibrate_data[6])
    p2 = float(clibrate_data[7])
    k3 = float(clibrate_data[8])

    # 畸变系数
    # dist_coeffs = np.array([k1, k2, p1, p2, k3]).reshape((1,5))
    dist_coeffs = (k1, k2, p1, p2)

    return cam_mat, dist_coeffs

def raw2ref(xmp,img):

    """
    DN值转反射率
    img为数组
    """

    # 黑电平
    blacklevel = exif['Exif.Image.BlackLevel']
    blacklevel = int(blacklevel)

    # sens0rgain 增益
    sensorgain = float(xmp['Xmp.drone-dji.SensorGain'])

    # ExposureTime 曝光时间
    ExposureTime = float(xmp['Xmp.drone-dji.ExposureTime'])

    # 暗角补偿图像中心
    CalibratedOpticalCenterX = float(xmp['Xmp.drone-dji.CalibratedOpticalCenterX'])
    CalibratedOpticalCenterY = float(xmp['Xmp.drone-dji.CalibratedOpticalCenterY'])

    # 暗角补偿多项式系数
    VignettingData = xmp[
        'Xmp.drone-dji.VignettingData']  # '0.000218235, 1.20722e-6, -2.8676e-9, 5.1742e-12, -4.16853e-15, 1.36962e-18'
    VignettingData = VignettingData.split(",")
    VignettingData = [float(i) for i in VignettingData]

    # pcamera_band
    pcamera_band = float(xmp['Xmp.drone-dji.SensorGainAdjustment'])

    # nirls*plsnir
    Camera_Irradiance = float(xmp['Xmp.Camera.Irradiance'])

    Band_canmera = np.zeros((h, w))

    # 数据归一化
    img = (img - blacklevel) / 65535

    # 暗角补偿
    for i in range(h):  # i对应y
        for j in range(w):  # j对应x

            r = ((j - CalibratedOpticalCenterX) ** 2 + (i - CalibratedOpticalCenterY) ** 2) ** 0.5

            correction = ((VignettingData[5]) * (r ** 6) + (VignettingData[4]) * (r ** 5) + (VignettingData[3]) * (
                        r ** 4) + (VignettingData[2]) * (r ** 3) + (VignettingData[1]) * (r ** 2)
                          + (VignettingData[0]) * r) + 1.0

            Band_canmera[i, j] = (img[i, j] * correction) / (sensorgain * ExposureTime / 1000000.0)

    # 计算反射率
    Band_ref = (Band_canmera * pcamera_band) / Camera_Irradiance

    return Band_ref

def dis_correction(cam_mat,dist_coeffs,Band_ref):

    '''
    优化相机内参（camera matrix），这一步可选。
    参数1表示保留所有像素点，同时可能引入黑色像素，
    设为0表示尽可能裁剪不想要的像素，这是个scale，0-1都可以取。
    '''

    (h,w) = Band_ref.shape

    # 优化内方位元素
    newcameramtx, roi = cv2.getOptimalNewCameraMatrix(cam_mat, dist_coeffs, (h, w), 0, (h, w))

    # 畸变校正
    dst = cv2.undistort(Band_ref, cam_mat, dist_coeffs, None, newcameramtx)

    print("newcameramtx:", newcameramtx)

    # 输出纠正畸变以后的图片
    x, y, w, h = roi

    dst = dst[y:y + h, x:x + w]


    return dst

if __name__ == '__main__':

    imagepath = r"C:\Users\admin\Desktop\test\DJI_002_2.TIF"
    outimage = r"C:\Users\admin\Desktop\test\DJI_002_2t.TIF"


    xmp, exif = image_info(imagepath)
    print("xmp is:", xmp)
    print("exif is:", exif)

    img = cv2.imread(imagepath, 2)

    h, w = img.shape
    print("h is:",h, w)
    print("w is:", w)

    cam_mat, dist_coeffs = image_mat(xmp)
    print("cam_mat is:", cam_mat)
    print("dist_coeffs is:", dist_coeffs)

    Band_ref = raw2ref(xmp, img)

    new_image = dis_correction(cam_mat, dist_coeffs, Band_ref)

    cv2.imwrite(outimage, new_image*1000)

#计算误差
# tot_error = 0
# for i in range(len(objpoints)):
#     imgpoints2, _ = cv2.projectPoints(objpoints[i], rvecs[i], tvecs[i], mtx, dist)
#     error = cv2.norm(imgpoints[i],imgpoints2, cv2.NORM_L2)/len(imgpoints2)
#     tot_error += error
# print ("total error: ", tot_error/len(objpoints))