import matplotlib.pyplot as plt
import boto3
import io
import os

s3r = boto3.resource('s3')

def create_validation_charts(request, context):

    y_val = request['y_val']
    preds = request['predictions']
    s3_model_path = request['s3_mdl_path']
    bucket_name = os.environ.get('S3_BUCKET_NAME')

    sub = [a-b for a, b in zip(y_val, preds)]
    # Create residual histogram and correlation plot
    fig,axs = plt.subplots(ncols=2,figsize=(18,8))
    fig.suptitle('BDS Model',fontsize=22)
    axs[0].set_title('Residual frequency distribution',fontsize=18)
    axs[0].set_xlabel('Residual',fontsize=16)
    axs[0].set_ylabel('Frequency',fontsize=16)
    #axs[0].set_xlim((-12, 17))
    #axs[0].set_ylim((0, 4500))
    axs[1].set_title('Comparison',fontsize=18)
    axs[1].set_xlabel('Bathymetry',fontsize=16)
    axs[1].set_ylabel('Prediction',fontsize=16)
    axs[0].hist(sub, bins=10)
    axs[1].plot(y_val,preds,'b.',y_val,y_val,'r')
    axs[0].grid(color='white')
    axs[1].grid(color='white')
    axs[0].spines["right"].set_visible(False)
    axs[0].spines["left"].set_visible(False)
    axs[0].spines["top"].set_visible(False)
    axs[0].spines["bottom"].set_visible(False)
    axs[1].spines["right"].set_visible(False)
    axs[1].spines["left"].set_visible(False)
    axs[1].spines["top"].set_visible(False)
    axs[1].spines["bottom"].set_visible(False)
    
    axs[0].set_facecolor((0.220, 0.217, 0.231, 0.1))
    axs[1].set_facecolor((0.220, 0.217, 0.231, 0.1))
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png')
    img_buffer.seek(0)
    img_path = f'{s3_model_path}/charts.png'

    print('Uploading figure to s3')
    try:
        #s3r.Object(bucket_name, img_path).put(Body=img_buffer.getvalue(), ContentType='image/png', ACL='public-read')
        bucket = s3r.Bucket(bucket_name)
        bucket.put_object(Body=img_buffer, ContentType='image/png', Key=img_path)
    except Exception as e:
        print(e)
        request['model_creating'] = False

        return request
    
    request['model_creating'] = True

    return request