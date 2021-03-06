import requests
import os
import pandas as pd
import rasterio
from datetime import datetime
import matplotlib.pyplot as plt
from rasterio.transform import Affine
import json
import numpy as np
from scipy.interpolate import Rbf


class get_data:
        def __init__(self ,year ,month ,day ,time):
            self.year = str(year)
            self.month = str(month)
            self.day = str(day)
            self.time = time
        ####################################################            
        def req(self, date):
            headers = {
                'authority': 'aqms.doe.ir',
                'sec-ch-ua': '"Google Chrome";v="93", " Not;A Brand";v="99", "Chromium";v="93"',
                'accept': 'application/json, text/javascript, */*; q=0.01',
                'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'x-requested-with': 'XMLHttpRequest',
                'sec-ch-ua-mobile': '?0',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36',
                'sec-ch-ua-platform': '"Windows"',
                'origin': 'https://aqms.doe.ir',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-mode': 'cors',
                'sec-fetch-dest': 'empty',
                'referer': 'https://aqms.doe.ir/Home/AQI',
                'accept-language': 'en-US,en;q=0.9,fa;q=0.8',
                'cookie': '_ga=GA1.2.693905583.1629652760; ASP.NET_SessionId=zld1snwkdwjqocaayfnfbtkl; _gid=GA1.2.516265215.1630662408',
            }

            data = {
              'Date': date,
              'type': '1'
            }

            response = requests.post('https://aqms.doe.ir/Home/GetAQIData/', headers=headers, data=data)

            return response
        #################################################
        def get_data_main(self):
            date = str(self.year) +"/"+ str(self.month) +"/"+ str(self.day) + " " + self.time
            resp = self.req(date)
            resp = resp.json()
            df = pd.DataFrame(resp['Data'])
            df = df[['StateName_En','StationName_En','StationName_Fa','CO','O3','O3','NO2','SO2','PM10', 'PM2_5','AQI','Pollutant','Date_Shamsi']]
            df = df[df['StateName_En']=='Tehran']
            return df

class Model_RBF:
        def __init__(self, North, South, East, West, Resolution, data, pollution, model_rbf, old_data):
            self.North = North 
            self.South =  South
            self.East = East 
            self.West = West
            self.Resolution = Resolution
            self.data = data[['StationName_En',pollution,'latitude','longtitude']].dropna().reset_index(drop=True)
            self.pollution = pollution
            self.dataset = None
            self.model_data = pd.DataFrame()
            self.row = None
            self.column = None
            self.boundary_latitudes = None
            self.boundary_longtitudes = None
            self.center_latitudes = None
            self.center_longtitudes = None
            self.model_rbf = model_rbf
            self.old_data = old_data
            self.N = 35.8272
            self.S = 35.5547
            self.E = 51.6133
            self.W = 51.1276

######################################################################################                
        def tiff_data (self, East, West, North, South):
            # find number of pixles with turn degree to meter
            number_of_pixels_x = int(((East - West)*(2*np.pi*6378100*np.cos(np.radians(South))))/(360*self.Resolution))
            number_of_pixels_y = int(((North - South)*(2*np.pi*6378100))/(360*self.Resolution))
            
            # find coordinate of pixels
            x = np.linspace(West, East, number_of_pixels_x + 1)
            y = np.linspace(South, North, number_of_pixels_y + 1)
            
            resy = float((y[-1] - y[0]) / number_of_pixels_y)
            resx = float((x[-1] - x[0]) / number_of_pixels_x)
            
            x1 = x - (resx / 2.0)
            y1 = y - (resy / 2.0)
            x1 = np.append(x1, (x1[-1]+resx))
            y1 = np.append(y1, (y1[-1]+resy))

            
            self.center_longtitudes, self.center_latitudes = np.meshgrid(x, y)
            self.boundary_longtitudes, self.boundary_latitudes = np.meshgrid(x1, y1)
            
            X =  self.center_longtitudes
            # print(X)
            raster = np.zeros([X.shape[0],X.shape[1]])

            #define transformation for Tiff file
            transform = Affine.translation(x[0] - resx / 2, y[0] - resy / 2) * Affine.scale(resx, resy)
            self.dataset = rasterio.open('sample.tif',
                          'w', 
                          driver='GTiff',
                          height = X.shape[0] , 
                          width = X.shape[1],
                          count=1,
                          dtype=X.dtype,
                          crs='+proj=latlong',
                          transform=transform,
                          )
            self.dataset.write(raster, 1)

            self.row = X.shape[0]
            self.column = X.shape[1]
            
            A_latitudes_points = np.delete(self.boundary_latitudes, -1, 0)
            A_latitudes_points = np.delete(A_latitudes_points, -1, 1)
            A_latitudes_points = A_latitudes_points.flatten()
            A_longtitudes_points = np.delete(self.boundary_longtitudes, -1, 0)
            A_longtitudes_points = np.delete(A_longtitudes_points, -1, 1)
            A_longtitudes_points = A_longtitudes_points.flatten()
            
            B_latitudes_points = np.delete(self.boundary_latitudes, -1, 0)
            B_latitudes_points = np.delete(B_latitudes_points, 0, 1)
            B_latitudes_points = B_latitudes_points.flatten()
            B_longtitudes_points = np.delete(self.boundary_longtitudes, -1, 0)
            B_longtitudes_points = np.delete(B_longtitudes_points, 0, 1)
            B_longtitudes_points = B_longtitudes_points.flatten()
            
            C_latitudes_points = np.delete(self.boundary_latitudes, 0, 0)
            C_latitudes_points = np.delete(C_latitudes_points, 0, 1)
            C_latitudes_points = C_latitudes_points.flatten()
            C_longtitudes_points = np.delete(self.boundary_longtitudes, 0, 0)
            C_longtitudes_points = np.delete(C_longtitudes_points, 0, 1)
            C_longtitudes_points = C_longtitudes_points.flatten()
            
            D_latitudes_points = np.delete(self.boundary_latitudes, 0, 0)
            D_latitudes_points = np.delete(D_latitudes_points, -1, 1)
            D_latitudes_points = D_latitudes_points.flatten()
            D_longtitudes_points = np.delete(self.boundary_longtitudes, 0, 0)
            D_longtitudes_points = np.delete(D_longtitudes_points, -1, 1)
            D_longtitudes_points = D_longtitudes_points.flatten()
         
            return A_longtitudes_points, A_latitudes_points, B_longtitudes_points, B_latitudes_points, C_longtitudes_points, C_latitudes_points, D_longtitudes_points, D_latitudes_points         
######################################################################################
        def data_arrange (self):
            
            # index stations locations in raster file
            pixely , pixelx = self.dataset.index(self.data['longtitude'], self.data['latitude'])
            pixelx = np.array(pixelx)
            pixely = np.array(pixely)

            self.model_data['StationName_En'] = self.data['StationName_En']
            self.model_data[self.pollution] = self.data[self.pollution]
            self.model_data['latitudes'] = self.data['latitude']
            self.model_data['longtitudes'] = self.data['longtitude']
            self.model_data['pixelx'] = pixelx
            self.model_data['pixely'] = pixely

            self.model_data.index = np.arange(len(self.model_data))
            self.dataset.close()
            os.remove("sample.tif")
######################################################################################
        def crop(self):
            # top right
            py1, px1 = self.dataset.index(self.E, self.N)
            # bottom right
            py2, px2 = self.dataset.index(self.E, self.S)
            # top left
            py3, px3 = self.dataset.index(self.W, self.N)
            # bottom left
            py4, px4 = self.dataset.index(self.W, self.S)

#             py1 = self.row - py1
#             py4 = self.row - py4

            return py1+1 , py4 , px1-1 , px4
######################################################################################        
        def scipy_idw(self, x, y, z, xi, yi):
            interp = Rbf(x, y, z, function= self.model_rbf)
            return interp(xi, yi)
######################################################################################    
        def rbf(self):
            df = pd.DataFrame()
            
            ALongtitudes ,ALatitudes, BLongtitudes ,BLatitudes, CLongtitudes ,CLatitudes, DLongtitudes ,DLatitudes = self.tiff_data(East = self.East, West = self.West, North = self.North, South= self.South)
            self.data_arrange()

            gridx = np.arange(0.0, self.column, 1)
            gridy = np.arange(0.0, self.row, 1)
            xi, yi = np.meshgrid(gridx, gridy)

            x = self.model_data['pixelx'],
            y = self.model_data['pixely'],
            z = self.model_data[self.pollution],

            rbf_result = self.scipy_idw(x,y,z,xi, yi) 
            
            py1 , py4 , px1 , px4 = self.crop()
            cropped_rbf = rbf_result[py4:py1 , px4:px1]
                        
            cropped_ALongtitudes ,cropped_ALatitudes, cropped_BLongtitudes ,cropped_BLatitudes, cropped_CLongtitudes ,cropped_CLatitudes, cropped_DLongtitudes ,cropped_DLatitudes = self.tiff_data(East = self.E, West = self.W, North = self.N, South= self.S)
            self.data_arrange()
            
            df[self.pollution] = np.around(cropped_rbf.flatten(), decimals=2)  
            df['ALongtitudes'] = np.around(cropped_ALongtitudes, decimals=4) 
            df['ALatitudes'] = np.around(cropped_ALatitudes, decimals=4) 
            df['BLongtitudes'] = np.around(cropped_BLongtitudes, decimals=4) 
            df['BLatitudes'] = np.around(cropped_BLatitudes, decimals=4) 
            df['CLongtitudes'] = np.around(cropped_CLongtitudes, decimals=4) 
            df['CLatitudes'] = np.around(cropped_CLatitudes, decimals=4) 
            df['DLongtitudes'] = np.around(cropped_DLongtitudes, decimals=4) 
            df['DLatitudes'] = np.around(cropped_DLatitudes, decimals=4) 

            return df, cropped_ALongtitudes, cropped_ALatitudes, cropped_BLongtitudes, cropped_BLatitudes, cropped_CLongtitudes, cropped_CLatitudes, cropped_DLongtitudes, cropped_DLatitudes ,cropped_rbf.flatten()

def turn_to_json(data, year, month, day, time, pollutions, directory = None):
    indicator = []

    for i in range(len(data['PM2_5'])):
            x = {}
            y_1 = {'ALongitude' : data['PM2_5']['ALongtitudes'][i]}
            x.update(y_1)
            y_2 = {'ALatitude' : data['PM2_5']['ALatitudes'][i]}
            x.update(y_2)
            y_3 = {'BLongitude' : data['PM2_5']['BLongtitudes'][i]}
            x.update(y_3)
            y_4 = {'BLatitude' : data['PM2_5']['BLatitudes'][i]}
            x.update(y_4) 
            y_5 = {'CLongitude' : data['PM2_5']['CLongtitudes'][i]}
            x.update(y_5)
            y_6 = {'CLatitude' : data['PM2_5']['CLatitudes'][i]}
            x.update(y_6) 
            y_7 = {'DLongitude' : data['PM2_5']['DLongtitudes'][i]}
            x.update(y_7)
            y_8 = {'DLatitude' : data['PM2_5']['DLatitudes'][i]}
            x.update(y_8) 
            for pollution in pollutions:
                    y_9 = {pollution : data[pollution][pollution][i]}
                    x.update(y_9)
            indicator.append(x)
            
    json_data = {
        "Date": datetime(year, month, day).strftime("%Y%m%d"),
        "Time": time,
        "indicator":indicator
    }
    
    return json_data


def main_polygon_value(year = 1400,month = 11, day = 20, time ='11:00'):
    North_coordinate = 36.2308
    South_coordinate = 35
    East_coordinate = 52.4688
    West_coordinate = 50
    Resolution = 250
    # new_excel_path = os.path('./asena/modules/stations_of_iran_new.xlsx')
    # old_excel_path = os.path('./asena/modules/stations_of_iran_old.xlsx')
    pollutions = ['CO', 'O3', 'NO2', 'SO2',	'PM10',	'PM2_5']
    AQI_pollutions = ['id','CO', 'O3', 'NO2', 'SO2', 'PM10', 'PM2_5','AQI']

    p = get_data(year=year, month=month, day=day, time=time)
    df = p.get_data_main()

    stations = pd.read_excel('./modules/stations_of_iran_new.xlsx')
    df_tehran = pd.merge(df, stations, on=['StationName_En'])
    df_tehran = df_tehran.loc[:, ~df_tehran.columns.duplicated()]

    old_stations = pd.read_excel('./modules/stations_of_iran_old.xlsx')
    final_df = {}
    rbf = pd.DataFrame()

    for pollution in pollutions: 
        final_df[pollution] = pd.DataFrame()
        p1 = Model_RBF(North = North_coordinate, South = South_coordinate, East = East_coordinate, 
            West = West_coordinate, Resolution = Resolution,
            data = df_tehran ,pollution = pollution, model_rbf = 'linear' , old_data = old_stations)
        final_df[pollution], xa, ya, xb, yb, xc, yc, xd, yd, rbf_values = p1.rbf()
        rbf[pollution] = rbf_values

    rbf['AQI'] = np.around(rbf.max(axis = 1), decimals=2)
    rbf['ALongtitudes'] = xa
    rbf['ALatitudes'] = ya
    rbf['BLongtitudes'] = xb
    rbf['BLatitudes'] = yb
    rbf['CLongtitudes'] = xc
    rbf['CLatitudes'] = yc
    rbf['DLongtitudes'] = xd
    rbf['DLatitudes'] = yd
    rbf['id'] = (rbf.index + 1)
    rbf['id'] = rbf['id'].astype({'id': float})

    final_df['AQI'] = rbf[['AQI', 'ALongtitudes', 'ALatitudes', 'BLongtitudes', 'BLatitudes', 'CLongtitudes', 'CLatitudes','DLongtitudes','DLatitudes']]
    final_df['id'] = rbf[['id', 'ALongtitudes', 'ALatitudes', 'BLongtitudes', 'BLatitudes', 'CLongtitudes', 'CLatitudes','DLongtitudes','DLatitudes']]

    json_file = turn_to_json(data = final_df, year = year, month = month, day = day, time = time, pollutions = AQI_pollutions)

    return json_file



