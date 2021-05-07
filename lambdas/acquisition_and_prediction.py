import pandas as pd
import numpy as np
import joblib as jb
from io import BytesIO, StringIO
import boto3
import json
import ee
import requests
from glob import glob
import tifffile
import requests
import zipfile
import os


s3_client = boto3.client('s3')
s3r = boto3.resource('s3')

def ndwi(first_band, second_band):
    """Apply ndwi filter to a pair of images

    Args:
        first_band [array]: First band to use on ndwi
        second_band [array]: Second band to use on ndwi

    Returns:
        [None | array]: Return 2d array containing ndwi image or None if images have different shapes
    """

    if first_band.shape != second_band.shape:
        return None

    output = np.zeros(first_band.shape)

    for i in range(first_band.shape[0]):
        for j in range(first_band.shape[1]):
            temp1 = first_band[i][j] - second_band[i][j]
            temp2 = first_band[i][j] + second_band[i][j]

            if temp2 == 0:
                output[i][j] = 1
                print(f'Math error on pixel [{i}][{j}], cannot divide by 0 - Assigning 1 to pixel value')
            else:
                temp3 = temp1/temp2
                output[i][j] = temp3
                
    return output

def acquisition_and_prediction(request, context):
    """
    {
        model_id: int,
        s3_mdl_path: str,
        prediction_name: str,
        user_email: str,
        image_date: str
    }
    """
    global credentials_dict
    global s3_client
    
    service_account = credentials_dict['client_email']
    with open('/tmp/ee_private_key.json', 'w') as f:
        json.dump(credentials_dict, f, indent=4)

    print('Initialize ee')
    credentials = ee.ServiceAccountCredentials(service_account, '/tmp/ee_private_key.json')
    ee.Initialize(credentials)

    deserilizer = ee.deserializer.fromJSON(request['gee_image_data'])
    single_image = ee.Image(deserilizer)

    image = single_image.reduceNeighborhood(ee.Reducer.median(),ee.Kernel.square(150, 'meters'))

    roi = image.geometry().getInfo()['coordinates'][0]

    params = {"scale": 30, "filePerBand":True, "crs": "EPSG:4326", 'region': roi}
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
        request['prediction_creating'] = False
        return request

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

    print('creating ndwi mask')
    # Create ndwi mask
    ndwi_image = ndwi(bands_arrays_dict['b3'], bands_arrays_dict['b8'])
    mask = (ndwi_image > 0.3)*255

    # Create dataframe for ndwi mask
    get_coords = True
    aux_dict_df = dict()
    aux_dict_df['coords_x'] = list()
    aux_dict_df['coords_y'] = list()

    for k, v in bands_arrays_dict.items():
        print(k)
        aux_dict_df[k] = list()
        for row, y in enumerate(mask):
            for col, x in enumerate(y):
                if mask[row][col]:
                    aux_dict_df[k].append(v[row][col])

                    if get_coords:
                        coord_x = long + (scale_long * col)
                        coord_y = lat + (scale_lat * row)
                        aux_dict_df['coords_x'].append(coord_x)
                        aux_dict_df['coords_y'].append(coord_y)

        if get_coords:
            get_coords = False

    df_all_image = pd.DataFrame(aux_dict_df)

    # Read raw bat dataframe from s3 bucket
    bucket_name = 'sentinel-cassie'
    prediction_formated_name = request['prediction_name'].strip().lower().replace(' ', '_')
    mdl_path = '{}/{}'.format(request['s3_mdl_path'], 'lgbm_model.pkl.z')
    df_all_image_name = '{}/{}'.format(request['s3_mdl_path'], prediction_formated_name)
    #df_all_image_name = f'{base_path}/df_all_image.csv'

    request['s3_prediction_path'] = df_all_image_name
    # Load model from s3
    try:
        with BytesIO() as f:
            s3_client.download_fileobj(Bucket='sentinel-cassie', Key=mdl_path, Fileobj=f)
            f.seek(0)
            mdl = jb.load(f)
    except Exception as e:
        print(e)
        request['prediction_creating'] = False
        return request
    

    predictions = mdl.predict(df_all_image.drop(['coords_x', 'coords_y'], axis=1))
    df_all_image['z_predict'] = predictions

    # Upload df to s3 bucket with uuid path
    csv_buffer_predictions = StringIO()
    df_all_image.to_csv(csv_buffer_predictions, index=None)

    try:
        s3r.Object(bucket_name, df_all_image_name).put(Body=csv_buffer_predictions.getvalue())
    except Exception as e:
        print(e)
        request['prediction_creating'] = False
        return request

    request['prediction_creating'] = True
    return request
