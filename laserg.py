
from PIL import Image
import os.path
import subprocess

# uses the alpha channel for the laser intensity
def convert_image_A_to_laser(img):
    img = img.convert('LA')
    s = img.split()
    return s[1].point(lambda v: 255 if v > 127 else 0)

# uses the image luminance for the laser intensity
def convert_image_L_to_laser(img):
    return img.convert('L')


def mm_to_img_xpos(v, dpi):
    return round(v * dpi / 25.4)

def mm_to_img_ypos(v, img, dpi):
    return img.height - round(v * dpi / 25.4) - 1

def img_xpos_to_mm(v, dpi):
    return v * 25.4 / dpi

def img_ypos_to_mm(v, height, dpi):
    v = height - v - 1
    return v * 25.4 / dpi

def find_laser_start_posx(data, w, h, dpi):
    x = 0
    while x < w:
        y = 0
        while y < h:
            v = data[x + w * y]
            if v > 0: return img_xpos_to_mm(x, dpi)
            y += 1
        x += 1
    return 0

def find_laser_start_posy(data, w, h, dpi):
    y = h - 1
    while y >= 0:
        x = 0
        while x < w:
            v = data[x + w * y]
            if v > 0: return img_ypos_to_mm(y, h, dpi)
            x += 1
        y -= 1
    return 0

def find_laser_end_posx(data, w, h, dpi):
    x = w - 1
    while x >= 0:
        y = 0
        while y < h:
            v = data[x + w * y]
            if v > 0: return img_xpos_to_mm(x, dpi)
            y += 1
        x -= 1
    return 0

def find_laser_end_posy(data, w, h, dpi):
    y = 0
    while y < h:
        x = 0
        while x < w:
            v = data[x + w * y]
            if v > 0: return img_ypos_to_mm(y, h, dpi)
            x += 1
        y += 1
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

def write_segment(gc, lum, ie, gy, dpi, bbox, feed, switch_laser_on, switch_laser_off, min_intensity, max_intensity):
    startx, starty, endx, endy = bbox
    gx = img_xpos_to_mm(ie, dpi)
    if lum == 0: # skip
        #gc.write("(disable laser: skip start=%d end=%d)\n" % (istart, iend))
        gc.write(switch_laser_off + "\n")
        gc.write("G0 X%f Y%f\n" % (gx - startx, gy - starty))
    else:
        #gc.write("(enable laser: start=%d end=%d lum=%d)\n" % (istart, iend, lum))
        gc.write((switch_laser_on + "\n" ) % (lum_to_spindel(lum, min_intensity, max_intensity)))
        gc.write("G1 X%f Y%f F%f\n" % (gx - startx, gy - starty, feed))
        
def image_to_gcode(file_name, img_converter, invert, bbox, dpi, mm_per_sec, laser_diameter, switch_laser_on, switch_laser_off, min_intensity, max_intensity):

    print("exporting:", file_name)

    image = Image.open(file_name)
    image = img_converter(image)
    if invert:
        image = image.point(lambda v: 255 - v)

    save_file = os.path.splitext(file_name)[0] + '.ngc'
    gc = open(save_file, 'w')

    feed = mm_per_sec * 60 # mm/s to mm/min
    left_to_right = True
    
    gc.write("(Generated with laserg: github.com/chsc/laserg)\n")
    gc.write("(file: %s)\n" % (file_name))
    gc.write("(image size in pixel: %s)\n" % (image.size,))
    gc.write("(bbox in mm: %s" % (bbox, ))
    gc.write("(pixel size: %f mm)\n" % (25.4 / dpi))
    gc.write("(laser diameter: %f mm)\n" % (laser_diameter))
    gc.write("(absolute positioning on)\n")
    gc.write("G90\n")
    gc.write("(move to start)\n")
    gc.write("G0 X0.0 Y0.0 Z0.0\n") # to start

    startx, starty, endx, endy = bbox

    gy = starty
    while gy <= endy:
        line = mm_to_img_ypos(gy, image, dpi)
        #print("laser pos: ", gy, "img line:", line)
        if left_to_right:
            gc.write("(move to line %d, left to right)\n" % (line))
            cont = True
            gx = startx
            while cont:
                ix = mm_to_img_xpos(gx, dpi)
                lum, istart, iend = color_segment(image, line, ix)
                gx = img_xpos_to_mm(iend, dpi)
                if gx > endx:
                    if lum == 0:
                        break
                    else:
                        gx = endx
                        iend = mm_to_img_xpos(gx, dpi)
                        cont = False
                write_segment(gc, lum, iend, gy, dpi, bbox, feed, switch_laser_on, switch_laser_off, min_intensity, max_intensity)
                if not cont: # move up
                    gc.write(switch_laser_off + "\n")
                    gc.write("G0 X%f Y%f\n" % (endx - startx, gy + laser_diameter - starty))
            left_to_right = False
        else:
            gc.write("(move to line %d, right to left)\n" % (line))
            gx = endx
            cont = True
            while cont:
                ix = mm_to_img_xpos(gx, dpi)
                lum, istart, iend = color_segment_back(image, line, ix)               
                gx = img_xpos_to_mm(iend, dpi)
                if gx < startx:
                    if lum == 0:
                        break
                    else:
                        gx = startx
                        iend = mm_to_img_xpos(gx, dpi) - 1
                        cont = False
                write_segment(gc, lum, iend + 1, gy, dpi, bbox, feed, switch_laser_on, switch_laser_off, min_intensity, max_intensity)
                if not cont:
                    gc.write(switch_laser_off + "\n")
                    gc.write("G0 X%f Y%f\n" % (0.0, gy + laser_diameter - starty))
            left_to_right = True
        gy += laser_diameter

    gc.write(switch_laser_off + "\n")
    gc.write("G0 X0.0 Y0.0\n") # back to start
    
    gc.close()
    #pixels.show()

def get_image_bbox(file_name, conv_func, invert, dpi):
    image = Image.open(file_name)
    image = conv_func(image)
    if invert: image = image.point(lambda v: 255 - v)

    print("Find bbox ...")
    pdata = image.getdata()
    startx = find_laser_start_posx(pdata, image.width, image.height, dpi)
    print("startx:", startx)
    starty = find_laser_start_posy(pdata, image.width, image.height, dpi)
    print("starty:", starty)
    endx = find_laser_end_posx(pdata, image.width, image.height, dpi)
    print("endx:", endx)
    endy = find_laser_end_posy(pdata, image.width, image.height, dpi)
    print("endy:", endy)
    
    return (startx, starty, endx, endy)

def export_svgs_to_pngs(directory, inkscape_executable, dpi, area):
    x0, y0, x1, y1 = area
    for file_name in os.listdir(directory):
        if file_name.endswith(".svg"):
            print("converting:", file_name)
            outfile = os.path.splitext(file_name)[0] + '.png'
            subprocess.check_call([
                inkscape_executable,
                "--without-gui",
                "--export-png=""%s""" % (os.path.join(directory, outfile)),
                "--export-dpi=%d" %(dpi),
                "--export-area=%d:%d:%d:%d" % (x0, y0, x1, y1),
                os.path.join(directory, file_name)])

def export_pcb(directory, base_name, dpi, area, is_positive_film, mm_per_sec, laser_diameter, switch_laser_on, switch_laser_off, intensity):

    export_svgs_to_pngs(directory, "inkscape", dpi, area)

    file_name_base = os.path.join(directory, base_name)

    cut_file = file_name_base + '-Edge_Cuts.png'
    cu_f_file = file_name_base + '-F_Cu.png'
    cu_b_file = file_name_base + '-B_Cu.png'
    mask_f_file = file_name_base + '-F_Mask.png'
    mask_b_file = file_name_base + '-B_Mask.png'
    silk_f_file = file_name_base + '-F_SilkS.png'
    silk_b_file = file_name_base + '-B_SilkS.png'
    paste_f_file = file_name_base + '-F_Paste.png'
    paste_b_file = file_name_base + '-B_Paste.png'

    # we use the cut out to calculate the dimesions of the board
    bbox = get_image_bbox(cut_file, convert_image_A_to_laser, False, dpi)

    # export them only if they exist

    # export front
    if(os.path.exists(cu_f_file)):
        image_to_gcode(cu_f_file, convert_image_A_to_laser, is_positive_film, bbox, dpi, mm_per_sec, laser_diameter, switch_laser_on, switch_laser_off, 0, intensity)
    if(os.path.exists(silk_f_file)):
        image_to_gcode(silk_f_file, convert_image_A_to_laser, False, bbox, dpi, mm_per_sec, laser_diameter, switch_laser_on, switch_laser_off, 0, intensity)
    if(os.path.exists(mask_f_file)):
        image_to_gcode(mask_f_file, convert_image_A_to_laser, False, bbox, dpi, mm_per_sec, laser_diameter, switch_laser_on, switch_laser_off, 0, intensity)
    if(os.path.exists(paste_f_file)):
        image_to_gcode(paste_f_file, convert_image_A_to_laser, False, bbox, dpi, mm_per_sec, laser_diameter, switch_laser_on, switch_laser_off, 0, intensity)

    # export back
    if(os.path.exists(cu_b_file)):
        image_to_gcode(cu_b_file, convert_image_A_to_laser, is_positive_film, bbox, dpi, mm_per_sec, laser_diameter, switch_laser_on, switch_laser_off, 0, intensity)
    if(os.path.exists(silk_b_file)):
        image_to_gcode(silk_b_file, convert_image_A_to_laser, False, bbox, dpi, mm_per_sec, laser_diameter, switch_laser_on, switch_laser_off, 0, intensity)
    if(os.path.exists(mask_b_file)):
        image_to_gcode(mask_b_file, convert_image_A_to_laser, False, bbox, dpi, mm_per_sec, laser_diameter, switch_laser_on, switch_laser_off, 0, intensity)
    if(os.path.exists(paste_b_file)):
        image_to_gcode(paste_b_file, convert_image_A_to_laser, False, bbox, dpi, mm_per_sec, laser_diameter, switch_laser_on, switch_laser_off, 0, intensity)

def export_image(file_name, invert, mm_per_sec, laser_diameter, switch_laser_on, switch_laser_off, min_intensity, max_intensity):
    image_to_gcode(file_name, convert_image_A_to_laser, is_positive_film, mm_per_sec, laser_diameter, switch_laser_on, switch_laser_off, min_intensity, max_intensity)

# Parameters
pcb_directory = "test"
pcb_base_name = "test"
pcb_area = (200, 600, 400, 700) # roughly where the pcb traces are in the input files
mm_per_sec = 20 # speed while exposing
laser_diameter = 0.05 # in mm
img_dpi = 600 # dpi of our original image file
is_photo_positive = True # False for photo-negative exposure and True for phot-positive
switch_laser_off = "M5" # command for switchin the laser off
switch_laser_on = "M3 S%f" # command for switching the laser on; spindle speed corresponds to the laser intensity
pcb_intensity = 10

export_pcb(pcb_directory, pcb_base_name, img_dpi, pcb_area, is_photo_positive, mm_per_sec, laser_diameter, switch_laser_on, switch_laser_off, pcb_intensity)

#file_name = "test.png"
#min_intensity = 500 # spindle speed for a pixel value of 0
#max_intensity = 900 # spindle speed for a pixel value of 255
# conv_func = convert_image_L_to_laser # use the alpha channel to control the laser. good for svgs/gerbers masks with transparency; for images use convert_image_L_to_laser.
#export_image(file_name, conv_func, invert, mm_per_sec, laser_diameter, switch_laser_on, switch_laser_off, min_intensity, max_intensity)







