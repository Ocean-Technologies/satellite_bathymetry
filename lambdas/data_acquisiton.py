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


credentials_dict = credentials_dict = {
  "type": "service_account",
  "project_id": os.environ.get('PROJECT_ID'),
  "private_key_id": os.environ.get('PRIVATE_KEY_ID'),
  "private_key": os.environ.get('PRIVATE_KEY'),
  "client_email": os.environ.get('CLIENT_EMAIL'),
  "client_id": os.environ.get('CLIENT_ID'),
  "auth_uri": os.environ.get('AUTH_URI'),
  "token_uri": os.environ.get('TOKEN_URI'),
  "auth_provider_x509_cert_url": os.environ.get('AUTH_PROVIDER_X509_CERT_URL'),
  "client_x509_cert_url": os.environ.get('CLIENT_X509_CERT_URL')
}
def medianValueAtPixel(px,py,image):
    p = list()
    for i in range(7):
        for j in range(7):
            y_index = py-3+i
            x_index = px-3+j
            if(y_index >= 0 and y_index < image.shape[0] and x_index >= 0 and x_index < image.shape[1]):
                p.append(image[y_index][x_index])
    return np.median(p)


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

    sentinel_dataset  = ee.ImageCollection("COPERNICUS/S2")

    coordinates = ee.Geometry.Polygon(request['coordinates'])
    start_date = request['start_date']
    end_date = request['end_date']
    bucket_name = 'sentinel-cassie'
    raw_bat_path = request['raw_bat_path']

    sentinel_roi = sentinel_dataset.filterBounds(coordinates).filterDate(start_date, end_date).select(['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8'])
    mosaic = sentinel_roi.mosaic()

    #params = {"scale":25, "region":coordinates, "filePerBand":True}
    params = {"scale": 25, 'crs': 'EPSG:32722', "region": coordinates, "filePerBand":True}

    try:
        print('Downloading images')
        url = mosaic.getDownloadURL(params)
        r = requests.get(url, stream=True)

        file_name_zip = '/tmp/filename.zip'
        filename = '/tmp/mosaic'
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

    meters_per_angle = 40075000 / float(360)

    scale_x = (aux_dict['ModelTransformationTag'][0]) * meters_per_angle
    scale_y = aux_dict['ModelTransformationTag'][5] * meters_per_angle

    start_value_x = aux_dict['ModelTransformationTag'][3]
    start_value_y = aux_dict['ModelTransformationTag'][7]

    utm_long, utm_lat, _, _ = utm.from_latlon(start_value_y, start_value_x)

    bands_arrays_dict = {}
    for k, v in bands_dict.items():
        bands_arrays_dict[k] = v.asarray() / 6553.5

    print('creating ndwi mask')
    # Create ndwi mask
    ndwi_image = ndwi(bands_arrays_dict['b3'], bands_arrays_dict['b8'])
    mask = (ndwi_image > 0.3)*255

    # Create dataframe for ndwi mask
    get_coords = True
    aux_dict_df = dict()
    aux_dict_df['coords_x'] = list()
    aux_dict_df['coords_y'] = list()
    aux_dict_df['pixel_x'] = list()
    aux_dict_df['pixel_y'] = list()

    for k, v in bands_arrays_dict.items():
        print(k)
        aux_dict_df[k] = list()
        for row, y in enumerate(mask):
            for col, x in enumerate(y):
                if mask[row][col]:
                    median_value = medianValueAtPixel(col, row, v)
                    aux_dict_df[k].append(median_value)

                    if get_coords:
                        coord_x, coord_y = get_coord_from_pixel_pos(row, col, scale_x=25, scale_y=-25, start_x=utm_long, start_y=utm_lat)
                        aux_dict_df['coords_x'].append(coord_x)
                        aux_dict_df['coords_y'].append(coord_y)
                        aux_dict_df['pixel_x'].append(col)
                        aux_dict_df['pixel_y'].append(row)

        if get_coords:
            get_coords = False

    df_all_image = pd.DataFrame(aux_dict_df)

    # Upload df to s3 bucket with uuid path
    csv_buffer_all = io.StringIO()
    df_all_image.to_csv(csv_buffer_all, index=None)

    # Read raw bat dataframe from s3 bucket
    df_all_image_name = f'{s3_mdl_path}/df_all_image.csv'

    print('upload to bucket df all csv')
    try:
        s3r.Object(bucket_name, df_all_image_name).put(Body=csv_buffer_all.getvalue())
    except Exception as e:
        print(e)
        request['model_creating'] = False

        return request

    del df_all_image

    # Read raw bathymetry file from s3, must be on X, Y, Z format with this column order
    try:
        resp = s3_client.get_object(Bucket=bucket_name, Key=raw_bat_path)
        df_raw_bat = pd.read_csv(resp['Body'], sep=' ', header=None)
        df_raw_bat.columns = ['x', 'y', 'z']
    except Exception as e:
        print(e)
        request['model_creating'] = False

    df_pixel_coord_bat_data = pd.DataFrame()
    df_pixel_coord_bat_data['x'] = df_raw_bat['x'].apply(lambda x: int((x-utm_long)/float(scale_x)))
    df_pixel_coord_bat_data['y'] = df_raw_bat['y'].apply(lambda x: int((x-utm_lat)/float(scale_y)))
    df_pixel_coord_bat_data['z'] = df_raw_bat['z']

    df_variance = df_pixel_coord_bat_data.groupby(['x', 'y']).var().reset_index()
    df_variance = df_variance[df_variance.z > 0.05]

    df_pixel_coord_bat_data_mean = df_pixel_coord_bat_data.groupby(['x', 'y']).mean()
    df_pixel_coord_bat_data_mean.reset_index(inplace=True)

    df_pixel_coord_bat_data_mean = df_pixel_coord_bat_data_mean[~df_pixel_coord_bat_data_mean.index.isin(df_variance.index)]

    del df_variance
    del df_pixel_coord_bat_data

    print('upload to bucket df bat csv')
    df_pixel_coord_bat_data_mean_name = f'{s3_mdl_path}/df_bat.csv'
    
    # Upload bathymetry with bands reflectances to s3
    csv_buffer_bat = io.StringIO()
    df_pixel_coord_bat_data_mean.to_csv(csv_buffer_bat, index=None)
    try:
        s3r.Object(bucket_name, df_pixel_coord_bat_data_mean_name).put(Body=csv_buffer_bat.getvalue())
        #s3r.Object(bucket_name, train_data_name).put(Body=train_buffer.getvalue())
        #s3r.Object(bucket_name, test_data_name).put(Body=test_buffer.getvalue())
    except Exception as e:
        print(e)
        request['model_creating'] = False
        return request
    
    request['train_data_path'] = df_pixel_coord_bat_data_mean_name
    request['model_creating'] = True
    
    return request
