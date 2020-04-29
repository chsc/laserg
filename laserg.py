from PIL import Image
import os.path

# uses the alpha channel for the laser intensity
def convert_image_A_to_laser(img):
    img = img.convert('LA')
    s = img.split()
    #print(dir(s[1]))
    #img = Image.merge('L', [s[1]])
    #img.show()
    return s[1]

def convert_image_L_to_laser(img):
    return img.convert('L')

def mm_to_img_ypos(v, img):
    return img.height - round(v * dpi / 25.4) - 1

def img_xpos_to_mm(v):
    return v * 25.4 / dpi

def img_ypos_to_mm(v, height):
    v = height - v - 1
    return v * 25.4 / dpi

def img_size_in_mm(img):
    return ((img.width - 1) * 25.4 / dpi, (img.height-1) * 25.4 / dpi)

def find_laser_start_posy(pixels):
    y = pixels.height - 1
    while y > 0:
        x = 0
        while x < pixels.width:
            v = pixels.getpixel((x, y))
            if v > 0: return img_ypos_to_mm(y, pixels.height)
            x += 1
        y -= 1
    return 0

def find_laser_start_posx(pixels):
    x = 0
    while x < pixels.width:
        y = 0
        while y < pixels.height:
            v = pixels.getpixel((x, y))
            if v > 0: return img_xpos_to_mm(x)
            y += 1
        x += 1
    return 0

def lum_to_spindel(lum, min_intensity, max_intensity):
    v = lum / 255.0
    return min_intensity + v * (max_intensity - min_intensity)
    
def color_segment(img, line, x):
    lum = img.getpixel((x, line))
    nx = x + 1
    while nx < img.width and lum == img.getpixel((nx, line)):
        nx += 1
    return (lum, x, nx)

def color_segment_back(img, line, x):
    lum = img.getpixel((x, line))
    nx = x - 1
    while nx >= 0 and lum == img.getpixel((nx, line)):
        nx -= 1
    return (lum, x, nx)

def write_segment(gc, left_to_right, lum, istart, iend, gy, startx, starty, feed, min_intensity, max_intensity):
    gx = img_xpos_to_mm(iend - 1) if left_to_right else img_xpos_to_mm(iend)
    if lum == 0: # skip
        gc.write("(disable laser: skip start=%d end=%d)\n" % (istart, iend))
        gc.write(switch_laser_off + "\n")
        gc.write("G0 X%f Y%f\n" % (gx - startx, gy - starty))
    else:
        gc.write("(enable laser: start=%d end=%d lum=%d)\n" % (istart, iend, lum))
        gc.write((switch_laser_on + "\n" ) % (lum_to_spindel(lum, min_intensity, max_intensity)))
        gc.write("G1 X%f Y%f F%f\n" % (gx - startx, gy - starty, feed))
        
def image_to_gcode(file_name, img_converter, invert, mm_per_sec, laser_diameter, min_intensity, max_intensity):
    image = Image.open(file_name)
    pixels = img_converter(image)
    if invert:
        pixels = pixels.point(lambda v: 255 - v)

    startx = find_laser_start_posx(pixels)
    starty = find_laser_start_posy(pixels)

    print(startx, starty)

    save_file = os.path.splitext(file_name)[0] + '.ngc'
    gc = open(save_file, 'w')

    feed = mm_per_sec * 60 # mm/s to mm/min
    left_to_right = True
    
    (img_width_mm, img_height_mm) = img_size_in_mm(pixels)

    gc.write("(Generated with laserg: github.com/chsc/laserg)\n")
    gc.write("(file: %s)\n" % (file_name))
    gc.write("(image size in pixel: %s)\n" % (pixels.size,))
    gc.write("(image size in mm: %f x %f)\n" % (img_width_mm, img_height_mm))
    gc.write("(pixel size: %f mm)\n" % (25.4 / dpi))
    gc.write("(laser diameter: %f mm)\n" % (laser_diameter))
    gc.write("(absolute positioning on)\n")
    gc.write("G90\n")
    gc.write("(move to start)\n")
    gc.write("G0 X0.0 Y0.0 Z0.0\n") # to start

    gy = 0
    while gy < img_height_mm:
        line = mm_to_img_ypos(gy, pixels)
        #print("laser pos: ", gy, "img line:", line)
        if left_to_right:
            #gc.write("(line %d, left to right)\n" % (line))
            ix = 0
            while ix < pixels.width:
                (lum, istart, iend) = color_segment(pixels, line, ix)
                if iend == pixels.width and lum == 0: # empty
                    #gc.write("(empty)\n")
                    break
                write_segment(gc, left_to_right, lum, istart, iend, gy, startx, starty, feed, min_intensity, max_intensity)
                ix = iend
            left_to_right = False
        else:
            #gc.write("(line %d, right to left)\n" % (line))
            ix = pixels.width - 1
            while ix >= 0:
                (lum, istart, iend) = color_segment_back(pixels, line, ix)
                if iend == -1 and lum == 0: # empty
                    #gc.write("(empty)\n")
                    break
                write_segment(gc, left_to_right, lum, istart, iend, gy, startx, starty, feed, min_intensity, max_intensity)
                ix = iend
            left_to_right = True
        gy += laser_diameter

    gc.write(switch_laser_off + "\n")
    gc.write("G0 X0.0 Y0.0\n") # back to start
            
    gc.close()
    
    #pixels.show()

# Parameters
file_name = "noname-F_Cu.png" # file to use
#file_name = "test.png"
mm_per_sec = 20 # speed while exposing
laser_diameter = 0.05 # in mm
dpi = 600 # dpi of our orifinal image file
invert = False # False for photo-negative exposure and True for phot-positive
switch_laser_off = "M5" # command for switchin the laser off
switch_laser_on = "M3 S%f" # command for switching the laser on; spindle speed corresponds to the laser intensity
min_intensity = 500 # spindle speed for a pixel value of 0
max_intensity = 900 # spindle speed for a pixel value of 255
conv_func = convert_image_A_to_laser # use the alpha channel to control the laser. good for svgs/gerbers masks with transparency; for images use convert_image_L_to_laser.

image_to_gcode(file_name, conv_func, invert, mm_per_sec, laser_diameter, min_intensity, max_intensity)





