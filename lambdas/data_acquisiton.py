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


credentials_dict = {
  "type": "service_account",
  "project_id": "geeapi-307822",
  "private_key_id": "f20399d49751ea96b3fa9710ad648ffae0e7d6f4",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCqrrmmEqUTJndd\nE4LpSisBj+BF+xLkMk7g+yjmmJU8yK9mxsXfxJMCAXeZqd0TIsVpQAKOk/jDfR8P\nCI7PRACXwYPTo49G9nTTIwIWMPUM3TfkuvTB6xuTwIAQixGp2Omep5n4rZFLSlyf\nu454I+m9WFsrCm/tWJ2gdczmyZmhgELXPc4+/DDp50E8/rfyP8iEyyyyCs1rAnNx\nCK7VPj7yL6F6Pa6WX5Mjwg3CDsz4KUbIOlJjLyVK+N1EOpgc/kAqBZ/37uY8iXyk\naUmO6iN6MytDtdpkEvVQYTS9kdQn+LeMOndBc7gngkhZzIay/Y+l3e1a5AOKnBT+\nV9Rf9F3ZAgMBAAECggEAISFTNdIuqp3v02hDI+dam64CuXK3wwWk2/TEhqYdabQG\nn+t7Yyjz5BLG1VPsbpd0PC7JkEVWpxN1YOSnW8H2X36XiRAZcovKN2V3NTmBh2K1\nQ7eqZK2vJ6nY8d0cq5xIFJyxvVxrdHLVscelKtrFtxQcdilLeoWV6xySjkWZhYhf\nyWqq+1JttZtRm/cE/x76JAL77FizNEDIMisfetO/AOF2Pgb1xtECUG6+h3BPW/05\nx8M1nHGqUg5uam5Oy+101CUQw4LUYZPpEgJ7ME0AS4WaxyH8Ug+lnVmIUw2ImpsL\ndTUoZoEINbst7E41hOozIqOcHQYmA1qYDjEE72y2dQKBgQDTbjAh42FFg0RMtEEd\nnCWivFSGgmpvCBmol6Tp3TJtob/zLo+STm7g56ds1TmFW1RtxWKOlf+jk1qmkNpX\nuSSTtfU2M1RIfe9qyCxkYaR22aLFT0DVsORX+Doh97HkNznoJvcjHbJzRJ8RSwXb\nKVZCF4rL6sFziqLMuzN+RZYAnwKBgQDOqZUkMpqYz3urHYa+vPpD/V4ULaRIJmqQ\neEi1nXuSHJEay6VXG8rCbQZYHLEUklW/dB9HXENamfW+lQOdf/+7wXvrIogk82wI\nXQBl2vsAZMwUo2bNMkmG919TuNt026RiwpEJPoLuGGj81CGntiyGME9AaqLF5ww7\nJUavkPe2hwKBgCZwcwnGOCoWKnWzk98ZQ3JpwQhPb6BOHbQcFdx63a826BoDThDw\nd5ImK7dKsNGBAEGQ0FFSDg8kPCfqT/gA7hh4zWMUQ++GDeAhEokRg4AkI0ayGPyA\n05L2y0LfsJToQXvmkantvULdp/nR5PeqdUdA1ngqbw9dlimYo00Cw7nLAoGAGhDV\nmM0xJpj01i5RMnmPb0fjt9PR5q/BvRsOwKluTo1/18tbvVLqDf/GTxK/WwLiAdXZ\npByE+kZ08mbFH/ZnAP10bcHbPh3dwGhKho5KHlCYVPoPG05+a6GDyoGEXIbfgv1b\nYbkatoEprMnsvMSDdSFevZc1lJSBvGwFMFuugr0CgYA6v03AK8hGYGMerNlAXRRv\nEftENzm7+B0p+RvcYtWqq1djwQgDBtj59aEqzTcuYqL358c8TJmt9H5G//KK+kCt\nqmDjlnl71FE5XLlSsVCnLOMAX8Uzpuhu3RPqAWSENJaUtit8YVOXaRm/+1hNMijt\n7BTdMA4CaW7AkQ9cLiJb+g==\n-----END PRIVATE KEY-----\n",
  "client_email": "cassiesentinel@geeapi-307822.iam.gserviceaccount.com",
  "client_id": "111696626366876739612",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/cassiesentinel%40geeapi-307822.iam.gserviceaccount.com"
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

    # TODO add this to request -> bat utm region
    bucket_name = 'sentinel-cassie'
    raw_bat_path = request['raw_bat_path']
    bat_utm_region_code = request['bat_utm_region_code']
    bat_utm_region_letter = request['bat_utm_region_letter']

    # TODO ADD THIS TO REQUEST
    deserilizer = ee.deserializer.fromJSON(request['gee_image_data'])
    image = ee.Image(deserilizer)

    #params = {"scale":25, "region":coordinates, "filePerBand":True}
    params = {"scale": 25, "filePerBand":True, "crs": "EPSG:4326"}
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
            aux.append(medianValueAtPixel(px, py, v))
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
