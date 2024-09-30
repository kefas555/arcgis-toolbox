# -*- coding: utf-8 -*-

import arcpy
import os
import imageio
import pandas as pd
import datetime as dt
from platform import system
from PIL import Image, ImageFont, ImageDraw
import arcgis
from arcgis.gis import GIS
from arcgis import geometry, geocode
from arcgis.raster.functions import apply


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [CreateMovie]


class CreateMovie(object):
    gis = GIS("https://www.arcgis.com")

    landsat_item = gis.content.get('d9b466d6a9e647ce8d1dd5fe12eb434b')
    landsat = landsat_item.layers[0]

    rgb_collection = apply(landsat, 'Natural Color with DRA')

    g = geocode('Marakech, Morocco', out_sr=3857)[0]
    extent = g.get('extent')

    m = gis.map('Marakech, Morocco')
    m.basemap = 'satellite'

    
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "CreateMovie"
        self.description = "Tool that will take as a parameters geo location and time pertiod and will produce gif file of satelite images"
        self.canRunInBackground = False


    from functools import lru_cache
    @lru_cache(maxsize=50)
    def load_font(self):
        try:
            if system()=='Windows':
                return ImageFont.truetype("arial.ttf", 30)
            elif system()=='Linux':
                return ImageFont.truetype("~/.fonts/truetype/dejavu/DejaVuSans.ttf", 30)
            else:
                return ImageFont.truetype("Arial.ttf", 30)
        except:
            return ImageFont.load_default()

    def collection(self, df, interval, start, end, height, width):
        images=[]
        if(interval=='m'):                                                                                     # monthly
            for i in range(int(start.split('-')[0]), int(end.split('-')[0])+1):
                for j in range(1,13):
                    selected = df[(df['AcquisitionDate'].dt.year == i) & (df['AcquisitionDate'].dt.month == j)]
                    id = selected['OBJECTID'].values.tolist()
                    if(len(id)>0):
                        self.rgb_collection.mosaic_by(method="LockRaster",lock_rasters=id)
                        img_name = 'img_'+str(i)+'-'+str(j)+'.jpg'
                        self.rgb_collection.export_image(bbox=self.extent, size=[height,width], f='image', 
                                                      save_folder='.', 
                                                      save_file=img_name)
                        img = Image.open(img_name).convert('RGB')
                        font = self.load_font()
                        draw = ImageDraw.Draw(img)
                        draw.text((550, 0),str(j)+'-'+str(i),(255,255,255),font=font)
                        images.append(img)
                        os.remove(img_name)
                        
        elif(interval=='y'):                                                                                  # yearly
            for i in range(int(start.split('-')[0]), int(end.split('-')[0])+1):
                selected = df[df['AcquisitionDate'].dt.year == i]
                id = selected['OBJECTID'].values.tolist()
                if(len(id)>0):
                    self.rgb_collection.mosaic_by(method='LockRaster',lock_rasters=id)
                    img_name = 'img_'+str(i)+'.jpg'
                    self.rgb_collection.export_image(bbox=extent, size=[height,width], f='image', 
                                                  save_folder='.', 
                                                  save_file=img_name)
                    img = Image.open(img_name).convert('RGB')
                    font = self.load_font()
                    draw = ImageDraw.Draw(img)
                    draw.text((550, 0),str(i),(255,255,255),font=font)    
                    images.append(img)
                    os.remove(img_name)
        
        return images

    def create_movie(self, target, interval, start, end, height, width, extent, duration):
        start_date = dt.datetime.strptime(start, '%Y-%m-%d')
        end_date = dt.datetime.strptime(end, '%Y-%m-%d')
        selected = target.filter_by(where='(Category = 1) AND (CloudCover <=0.5)',
                                 time=[start_date, end_date],
                                 geometry=arcgis.geometry.filters.intersects(extent))

        df = selected.query(out_fields='AcquisitionDate, GroupName, CloudCover, DayOfYear', 
                            order_by_fields='AcquisitionDate').sdf
        df['AcquisitionDate'] = pd.to_datetime(df['AcquisitionDate'], unit='ms')
        frames = self.collection(df, interval, start, end, height, width)
        imageio.mimsave('./movie'+'_'+interval+'.gif', frames, duration=duration)
        print('Movie Created')

    def getParameterInfo(self):
        """Define parameter definitions"""
        geo_location = arcpy.Parameter(
            displayName="Geo Location",
            name="geo_location",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        geo_location.value="Marakech, Morocco"
        start_date = arcpy.Parameter(
            displayName="Start date",
            name="start_date",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        start_date.value="2023-01-01"
        end_date = arcpy.Parameter(
            displayName="End date",
            name="end_date",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        end_date.value="2023-12-31"
        params = [geo_location, start_date, end_date]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        
        geo_location = parameters[0].valueAsText
        start_date = parameters[1].valueAsText
        end_date = parameters[2].valueAsText


        self.g = geocode(geo_location, out_sr=3857)[0]
        self.extent = self.g.get('extent')

        self.m = self.gis.map(geo_location)
        self.m.basemap = 'satellite'


        self.create_movie(self.rgb_collection,'m' , start_date, end_date, 1250, 450, self.extent, 0.4)
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return
