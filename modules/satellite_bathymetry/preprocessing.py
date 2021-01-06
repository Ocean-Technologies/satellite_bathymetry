import numpy as np
from tqdm.notebook import tqdm

def get_coord_from_pixel_pos(i, j, scale_x=10, scale_y=10, start_x=707160.0, start_y=7117780.0):
    """This functions get image data and returns the UTM coord for a pixel

    Args:
        coord_x         [int]: pixel X coord
        coord_y         [int]: pixel Y coord
        scale_x         [int]: image X scale
        scale_y         [int]: image Y scale
        start_value_x   [float]: start X coord (UTM)
        start_value_x   [float]: start Y coord (UTM)

    Returns:
        tuple [float]: UTM value for pixel
        e.g : (707170.0, 7117780.0)
    """

    return (start_x+scale_x*i, start_y-scale_y*j)

def get_pixel_from_coord(coord_x, coord_y, scale_x=10, scale_y=10, start_x=707160.0, start_y=7117780.0):
    """This functions get an UTM position and return the pixel position for that position
    Args:
        coord_x     [float]: UTM X coord
        coord_y     [float]: UTM Y coord
        scale_x     [int]:   image X scale
        scale_y     [int]:   image Y scale
        start_x     [float]: start X coord (UTM)
        start_y     [float]: start Y coord (UTM)

    Returns:
        tuple [int]: pixel position
        e.g : (1, 0)
    """

    return (int((coord_x-start_x)/scale_x), int((start_y-coord_y)/scale_y))


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

    for i in tqdm(range(first_band.shape[0])):
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