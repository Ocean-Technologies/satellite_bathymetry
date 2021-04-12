import seaborn as sns
import matplotlib.pyplot as plt
import boto3

s3r = boto3.resource('s3')

def create_validation_charts(request, context):

    y_val = request['y_val']
    preds = request['predictions']

   # Create residual histogram and correlation plot
    fig,axs = plt.subplots(ncols=2,figsize=(18,8))
    fig.suptitle('BDS Model',fontsize=22)
    axs[0].set_title('Residual frequency distribution',fontsize=18)
    axs[0].set_xlabel('Residual',fontsize=16)
    axs[0].set_ylabel('Frequency',fontsize=16)
    axs[0].set_xlim((-12, 17))
    axs[0].set_ylim((0, 4500))
    axs[1].set_title('Comparison',fontsize=18)
    axs[1].set_xlabel('Bathymetry',fontsize=16)
    axs[1].set_ylabel('Prediction',fontsize=16)
    sns.histplot(y_val-preds, bins=10,ax=axs[0])
    axs[1].plot(y_val,preds,'b.',y_val,y_val,'r')
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png')
    img_path = f'{s3_model_path}/charts.png'

    print('Uploading figure to s3')
    try:
        s3r.Bucket(bucket_name).put(Body=img_buffer, ContentType='image/png', Key=img_path)
    except Exception as e:
        print(e)
        request['model_creating'] = False

        return request
    
    request['model_creating'] = True

    return request