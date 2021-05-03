import uuid
import boto3
import io
import json
import requests
import zipfile
import os
import pandas as pd
import numpy as np
import utm
import ee
from glob import glob
import tifffile
from preprocessing import ndwi, get_coord_from_pixel_pos, get_pixel_from_coord


s3_client = boto3.client('s3')
s3r = boto3.resource('s3')





def data_acquisition(request, ctx):
    global s3_client
    global s3r
    global credentials_dict
    
    service_account = credentials_dict['client_email']

    with open('/tmp/ee_private_key.json', 'w') as f:
        json.dump(credentials_dict, f, indent=4)

    print('Initialize ee')
    credentials = ee.ServiceAccountCredentials(service_account, '/tmp/ee_private_key.json')
    ee.Initialize(credentials)

    # TODO add this to request -> bat utm region
    bucket_name = 'sentinel-cassie'
    raw_bat_path = request['raw_bat_path']
    
    #bat_utm_region_code = request['bat_utm_region_code']
    #bat_utm_region_letter = request['bat_utm_region_letter']

    # TODO ADD THIS TO REQUEST
    deserilizer = ee.deserializer.fromJSON(request['gee_image_data'])
    single_image = ee.Image(deserilizer)

    image = single_image.reduceNeighborhood(ee.Reducer.median(),ee.Kernel.square(150, 'meters'))

    roi = image.geometry().getInfo()['coordinates'][0]
    
    _,_,bat_utm_region_code,bat_utm_region_letter = utm.from_latlon(roi[0][1],roi[0][0])
    
    #params = {"scale":25, "region":coordinates, "filePerBand":True}
    params = {"scale": 50, "filePerBand":True, "crs": "EPSG:4326", 'region': roi}
    try:
        print('Downloading images')
        url = image.getDownloadURL(params)
        r = requests.get(url, stream=True)

        file_name_zip = '/tmp/filename.zip'
        filename = '/tmp/image'
        with open(file_name_zip, "wb") as fd:
            for chunk in r.iter_content(chunk_size=1024):
                fd.write(chunk)

        z = zipfile.ZipFile(file_name_zip)
        z.extractall(os.path.dirname(filename))
        z.close()
        os.remove(file_name_zip)
    except Exception as e:
        print(e)
        request['model_creating'] = False
        return request

    print("Creating bands dict")
    s3_mdl_path = request['s3_mdl_path'] #str(uuid.uuid4()).replace('-', '')

    path_data = '/tmp/'
    bands_list = [e for e in glob(str(path_data)+'/*') if e.endswith('.tif')]
    bands_list.sort()

    bands_dict = {}
    for i, e in enumerate(bands_list):
        bands_dict[f'b{i+1}'] = tifffile.TiffFile(e)

    aux_dict = dict()
    for page in bands_dict['b1'].pages:
        for tag in page.tags.values():
            aux_dict[tag.name] = tag.value

    scale_long = aux_dict['ModelTransformationTag'][0]
    scale_lat = aux_dict['ModelTransformationTag'][5]

    long = aux_dict['ModelTransformationTag'][3]
    lat = aux_dict['ModelTransformationTag'][7]

    bands_arrays_dict = {}
    for k, v in bands_dict.items():
        bands_arrays_dict[k] = v.asarray() / 6553.5

    # Read raw bathymetry file from s3, must be on X, Y, Z format with this column order
    try:
        resp = s3_client.get_object(Bucket=bucket_name, Key=raw_bat_path)
        df_raw_bat = pd.read_csv(resp['Body'], sep=' ', header=None)
        df_raw_bat.columns = ['x', 'y', 'z']
    except Exception as e:
        print(e)
        request['model_creating'] = False
        return request

    lat_list, long_list = utm.to_latlon(df_raw_bat.x.copy(), df_raw_bat.y.copy(), bat_utm_region_code, bat_utm_region_letter)

    df_raw_bat['lat'] = lat_list
    df_raw_bat['long'] = long_list

    df_pixel_coord_bat_data = pd.DataFrame()
    df_pixel_coord_bat_data['pixel_x'] = df_raw_bat['long'].apply(lambda x: int((x-long)/float(scale_long)))
    df_pixel_coord_bat_data['pixel_y'] = df_raw_bat['lat'].apply(lambda x: int((x-lat)/float(scale_lat)))
    df_pixel_coord_bat_data['lat'] = df_raw_bat['lat']
    df_pixel_coord_bat_data['long'] = df_raw_bat['long']
    df_pixel_coord_bat_data['z'] = df_raw_bat['z']

    mask_shape = bands_arrays_dict['b1'].shape
    df_masked = df_pixel_coord_bat_data[(df_pixel_coord_bat_data['pixel_x'] >= 0) & (df_pixel_coord_bat_data['pixel_x'] < mask_shape[0]) & (df_pixel_coord_bat_data['pixel_y'] >= 0) & (df_pixel_coord_bat_data['pixel_y'] < mask_shape[1])]
    
    for k, v in bands_arrays_dict.items():
        aux = list()
        for row in df_masked.itertuples():
            px = row.pixel_x
            py = row.pixel_y
            #aux.append(medianValueAtPixel(px, py, v))
            aux.append(v[py][px])
        df_masked[k] = aux


    df_variance = df_masked.groupby(['pixel_x', 'pixel_y']).var().reset_index()
    df_variance = df_variance[df_variance.z > 0.05]

    df_pixel_coord_bat_data_mean = df_masked.groupby(['pixel_x', 'pixel_y']).mean()
    df_pixel_coord_bat_data_mean.reset_index(inplace=True)

    df_pixel_coord_bat_data_mean = df_pixel_coord_bat_data_mean[~df_pixel_coord_bat_data_mean.index.isin(df_variance.index)]
    
    """
    return {
        "masked": len(df_masked),
        "df_pixel_coord_bat_data": len(df_pixel_coord_bat_data),
        "df_variance": len(df_variance),
        "df_pixel_coord_bat_data_mean": len(df_pixel_coord_bat_data_mean)
    }
    """

    del df_variance
    del df_pixel_coord_bat_data
    del df_masked

    print('upload to bucket df bat csv')
    df_pixel_coord_bat_data_mean_name = f'{s3_mdl_path}/df_bat.csv'
    
    # Upload bathymetry with bands reflectances to s3
    csv_buffer_bat = io.StringIO()
    df_pixel_coord_bat_data_mean.to_csv(csv_buffer_bat, index=None)
    try:
        s3r.Object(bucket_name, df_pixel_coord_bat_data_mean_name).put(Body=csv_buffer_bat.getvalue())
    except Exception as e:
        print(e)
        request['model_creating'] = False
        return request
    
    request['train_data_path'] = df_pixel_coord_bat_data_mean_name
    request['model_creating'] = True
    
    return request
