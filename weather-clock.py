#!/usr/bin/python
# -*- coding:utf-8 -*-

import sys
import os
import json
import urllib.request
import logging
from systemd.journal import JournaldLogHandler
import time
import datetime
import signal
import Adafruit_DHT
import urllib.request

# import e-ink library
libdir = '/home/pi/Downloads/e-Paper/RaspberryPi/python/lib/'
if os.path.exists(libdir):
    sys.path.append(libdir)
# for ePaper
from waveshare_epd import epd7in5_V2
from PIL import Image,ImageDraw,ImageFont


# temperature sensor model and pin number
DHT_SENSOR = Adafruit_DHT.DHT22
DHT_PIN = 4


######## All warning meaning from observatory, currently not use #######
# warning_keys = {
#     'WFIRE': '火災危險警告',
#     'WFIREY': '黃色火災危險警告',
#     'WFIRER': '紅色火災危險警告',
#     'WFROST': '霜凍警告',
#     'WHOT': '酷熱天氣警告',
#     'WCOLD': '寒冷天氣警告',
#     'WMSGNL': '強烈季候風信號',
#     'TC1': '一號戒備信號',
#     'TC3': '三號強風信號',
#     'TC8NE': '八號東北烈風或暴風信號',
#     'TC8SE': '八號東南烈風或暴風信號',
#     'TC8NW': '八號西南烈風或暴風信號',
#     'TC8SW': '八號西北烈風或暴風信號',
#     'TC9': '九號烈風或暴風風力增強信號',
#     'TC10': '十號颶風信號',
#     'WRAIN': '暴雨警告信號',
#     'WRAINA': '黃色暴雨警告信號',
#     'WRAINR': '紅色暴雨警告信號',
#     'WRAINB': '黑色暴雨警告信號',
#     'WFNTSA': '新界北部水浸特別報告',
#     'WL': '山泥傾瀉警告',
#     'WTCSGNL': '熱帶氣旋警告信號',
#     'WTMW': '海嘯警告',
#     'WTS': '雷暴警告'
# }

##### All icon number meaning from observator ##################
# icon_keys = {
#     '50': '陽光充沛',
#     '51': '間有陽光',
#     '52': '短暫陽光',
#     '53': '間有陽光 幾陣驟雨',
#     '54': '短暫陽光 有驟雨',
#     '60': '多雲',
#     '61': '密雲',
#     '62': '微雨',
#     '63': '雨',
#     '64': '大雨',
#     '65': '雷暴',
#     '70': '天色良好',
#     '71': '天色良好',
#     '72': '天色良好',
#     '73': '天色良好',
#     '74': '天色良好',
#     '75': '天色良好',
#     '76': '大致多雲',
#     '77': '天色大致良好',
#     '80': '大風',
#     '81': '乾燥',
#     '82': '潮濕',
#     '83': '霧',
#     '84': '薄霧',
#     '85': '煙霞',
#     '90': '熱',
#     '91': '暖',
#     '92': '涼',
#     '93': '冷'
# }

chi_days = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']

### Get the current date and time
now = datetime.datetime.now()
# format the date dd/mm/YY
mydate = now.strftime("%d/%m/%Y")
mytime = now.strftime("%H:%M")

# save the day count for later use (to loop on forecast each day)
mychi_day = chi_days[datetime.datetime.today().weekday()]

weather_today = None
weather_forecast = None
weather_warns = None
now_lastUpdateTime_str = None
fc_lastUpdateTime_str = None
indoor_humidity = 0
indoor_temp = 0

today_max_temp = 0
today_min_temp = 0
now_temp = 0.0
now_humid = 0
now_icon_num = 0
resdir = '/home/pi/Clock-Project/res/'
weatherPicsDir = '/home/pi/Clock-Project/res/weather-pics/'
fcPicsDir = '/home/pi/Clock-Project/res/weather-pics/fc/'
warningPicDir = '/home/pi/Clock-Project/res/weather-pics/warnings/'
today_min_max_file = "/home/pi/Clock-Project/weather-clock-info.json"
temp_data = {}
temp_data['TodayMinMaxTemperature'] = []
now_weather_area = 'Tuen Mun'
have_internet = False

epd = epd7in5_V2.EPD()
font24 = ImageFont.truetype(os.path.join(resdir, 'Font.ttc'), 24)
font37 = ImageFont.truetype(os.path.join(resdir, 'Font.ttc'), 37)
font55 = ImageFont.truetype(os.path.join(resdir, 'Font.ttc'), 55)
font127 = ImageFont.truetype(os.path.join(resdir, 'Font.ttc'), 127)
font158 = ImageFont.truetype(os.path.join(resdir, 'Font.ttc'), 158)
Himage = None
draw = None


# setup logging INFO
logging.basicConfig(level=logging.INFO)


# get an instance of the logger object this module will use
logger = logging.getLogger('weather-clock')
# instantiate the JournaldLogHandler to hook into systemd
journald_handler = JournaldLogHandler()
# set a formatter to include the level name
journald_handler.setFormatter(logging.Formatter(
    '[%(levelname)s] %(message)s'
))
# add the journald handler to the current logger
logger.addHandler(journald_handler)
# optionally set the logging level
logger.setLevel(logging.DEBUG)



def fetch_weather_info():
    global weather_today
    global weather_forecast
    global weather_warns
    global now_weather_area
    global now_temp
    global now_humid
    global now_icon_num
    global today_max_temp
    global today_min_temp
    global have_internet
    global now_lastUpdateTime_str
    global fc_lastUpdateTime_str

    global logger

    logger.info("Start weather update.")
    try:
        # fetch now weather, hk observatory has update every hour
        url = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=rhrread&lang=en"
        data = urllib.request.urlopen(url).read().decode()
        # parse json object
        weather_today = json.loads(data)

        # fetch 9 days weather forcast, hk observatory has 2 updates per day
        url = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=fnd&lang=en"
        data = urllib.request.urlopen(url).read().decode()
        weather_forecast = json.loads(data)

        # fetch weather warnings, hk observatory provide info "when needed"
        url = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=warnsum&lang=tc"
        data = urllib.request.urlopen(url).read().decode()
        weather_warns = json.loads(data)

        have_internet = True
    except:
        #logging.info("No internet!!")
        logger.info("No Internet!!")
        have_internet = False
        return

    # only do this if we got new update for "now weather"
    if weather_today["updateTime"] != now_lastUpdateTime_str:
        now_lastUpdateTime_str = weather_today["updateTime"]
        # find local area's temperature
        for place in weather_today['temperature']['data']:
            if place['place'] == now_weather_area:
                now_temp = place['value']
                break

        # there's only one humidity reading from observatory
        now_humid = weather_today['humidity']['data'][0]['value']

        # get the weather icon number (need fix for using the 1st item only?)
        now_icon_num = weather_today['icon'][0]
    else:
        logger.info("Got same weather update (now) from last time.")

    # only do this if we got new update for "weather forecast"
    if weather_forecast["updateTime"] != fc_lastUpdateTime_str:
        fc_lastUpdateTime_str = weather_forecast["updateTime"]
        logger.info("Have new weather (forecast) updates at %s", weather_forecast["updateTime"])

        # get today's max and min temperature forecast
        # hk observatory will release new forecast around 12 noon, once the new
        # forecast is released, the "today's max and min temperature" will be gone
        # therefore we need to save today's max and min in a json file for later use
        date_str = now.strftime("%Y%m%d")
        for forecast_day in weather_forecast['weatherForecast']:
            if forecast_day["forecastDate"] == date_str:
                today_min_temp = forecast_day['forecastMintemp']['value']
                today_max_temp = forecast_day['forecastMaxtemp']['value']

                ##### save today's min max temp to json file ######
                temp_data['TodayMinMaxTemperature'].append({
                    'updateTime' : weather_forecast["updateTime"],
                    'date' : date_str,
                    'min' : today_min_temp,
                    'max' : today_max_temp
                })
                # write to file
                with open(today_min_max_file, 'w') as outfile:
                    json.dump(temp_data, outfile)
                logger.info("Found today's min max temperature.  Today is %s", date_str)
                logger.info("Writing to JSON file = %s", today_min_max_file)
                #print("Found today's min max temperature = ", date_str)
                #print("Writing to JSON file = ", today_min_max_file)
                break

        # if we can't get the min max temperature from HK observatory
        # read from local json file
        if today_min_temp == 0:
            #print("Cannot found today's min max temperature, reading from old json file.")
            logger.info("Cannot found today's min max temperature, reading from old json file.")
            try:
                # read from json file
                with open(today_min_max_file) as json_file:
                    jsondata = json.load(json_file)
                for p in jsondata['TodayMinMaxTemperature']:
                    if p['date'] == date_str:
                        today_min_temp = p['min']
                        today_max_temp = p['max']
                        break
                    # if we can't find the min max temp even in the jason file
                    else:
                        logger.info("Cannont find today's min max temperature even in the json file.")
                        today_min_temp = 'NA'
                        today_max_temp = 'NA'
            except:
                logger.warning("Cannot find previous json file.")
                today_min_temp = 'NA'
                today_max_temp = 'NA'
    else:
        logger.info("Got same weather update (forecast) from last time.")



def fetch_indoor_info():
    try:
        global indoor_humidity
        global indoor_temp
        ### Get the indoor temperature and humidity from sensor ###
        indoor_humidity_raw, indoor_temp_raw = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
        indoor_humidity = int(round(indoor_humidity_raw))
        indoor_temp = int(round(indoor_temp_raw))
    except:
        logger.warning("Error getting indoor temperature and humidity from sensors.")


################### Start Drawing Here ######################################
#logging.info("init and Clear")

def epaper_draw_layout_lines():
    # draw all horizontal lines
    # format:
    # draw.line(( left, top, right, bottom) fill=0)   always fill 0 for black and white
    draw.line((0, 230, 400, 230), fill = 0)
    draw.line((0, 336, 800, 336), fill = 0)
    # draw all virtual lines
    draw.line((250, 230, 250, 336), fill = 0)
    draw.line((400, 0, 400, 230), fill = 0)
    draw.line((133, 336, 133, 480), fill = 0)
    draw.line((266, 336, 266, 480), fill = 0)
    draw.line((400, 336, 400, 480), fill = 0)
    draw.line((533, 336, 533, 480), fill = 0)
    draw.line((666, 336, 666, 480), fill = 0)


def epaper_draw_clock():
    # draw the clock area
    draw.text((20, 20), mydate, font = font37, fill = 0)
    draw.text((245,20), mychi_day, font = font37, fill = 0)
    draw.text((3, 53), mytime, font = font158, fill = 0)



def epaper_draw_main_weather():
    #### draw main weather area
    # draw the big weather icon
    main_weather_pic = Image.open(os.path.join(weatherPicsDir, str(now_icon_num) + '.png'))
    Himage.paste(main_weather_pic, (407,20))

    # big now temperature number
    draw.text((620, 20), str(now_temp), font = font127, fill = 0)
    draw.text((745, 20), '°C', font = font37, fill = 0)
    # upper and lower temperature for today
    draw.text((661, 175), '↑ ' + str(today_max_temp), font = font37, fill = 0)
    draw.text((740, 175), '°C', font = font24, fill = 0)
    draw.text((661, 225), '↓ ' + str(today_min_temp), font = font37, fill = 0)
    draw.text((740, 225), '°C', font = font24, fill = 0)

    # draw humidity now
    humidity_s_pic = Image.open(os.path.join(resdir, 'humidity-s.png'))
    Himage.paste(humidity_s_pic, (650, 280))
    draw.text((703, 280), str(now_humid)+"%", font = font37, fill = 0)


def epaper_draw_indoor_info():
    # draw indoor temperature and humidity
    house_pic = Image.open(os.path.join(resdir, 'house.png'))
    Himage.paste(house_pic, (10, 238))
    therometer_pic = Image.open(os.path.join(resdir, 'therometer.png'))
    Himage.paste(therometer_pic, (119, 240))
    humidity_s_pic = Image.open(os.path.join(resdir, 'humidity-s.png'))
    Himage.paste(humidity_s_pic, (112, 287))
    # house temperature and humidity
    draw.text((166, 238), str(indoor_temp), font = font37, fill = 0)
    draw.text((210, 238), '°C', font = font24, fill = 0)
    draw.text((166, 285), str(indoor_humidity)+'%', font = font37, fill = 0)


def epaper_draw_weather_warnings():
    # init warning pic x position
    warn_init_xpos = 262

    warnPicCnt = 0
    # draw all warnings
    for warn in weather_warns:
        # we can only put max of 5 warning on the screen
        if warnPicCnt < 5:
            warn_pic_file = weather_warns[warn]['code'].lower() + ".png"
            warn_pic = Image.open(os.path.join(warningPicDir, warn_pic_file))
            Himage.paste(warn_pic, (warn_init_xpos, 255))
            # the next warn pic x position
            warn_init_xpos += 76

            warnPicCnt += 1


def epaper_draw_all_forecast():
    # the first x-position for weekday names
    # since we have 6 weekday forcast, and resolution is 800x480
    # so each forcast square width is 800/6 = 133.333333333......
    fc_weekday_init_xpos = 32
    fc_pic_init_xpos = 36
    fc_temp_init_xpos = 33
    local_daycnt = datetime.datetime.today().weekday()

    # draw all weekday forcast boxes
    # we get the temperature day by day by searching the string
    for x in range(1,7):
        nextday = now.day + x
        # also set local_daycnt to next day
        # and back to monday if it's 7
        local_daycnt += 1
        if local_daycnt > 6:
            local_daycnt = 0

        date_str = now.strftime("%Y%m") + str(nextday)
        # loop through forcast days
        for forecast_day in weather_forecast['weatherForecast']:
            if forecast_day["forecastDate"] == date_str:
                fc_min_temp = forecast_day['forecastMintemp']['value']
                fc_max_temp = forecast_day['forecastMaxtemp']['value']
                fc_icon_num = forecast_day['ForecastIcon']

                # draw chinese weekday names
                draw.text((fc_weekday_init_xpos, 343), chi_days[local_daycnt], font = font24, fill = 0)

                # draw weather pic
                # fc_weather_pic = Image.open(os.path.join(resdir, 'sunny-fc.png'))
                fc_weather_pic = Image.open(os.path.join(fcPicsDir, str(fc_icon_num) + '.png'))
                Himage.paste(fc_weather_pic, (fc_pic_init_xpos, 375))

                # write Temperature
                draw.text((fc_temp_init_xpos, 442), str(fc_min_temp) + " - " + str(fc_max_temp), font = font24, fill = 0)

                # add 133 here as explained for all layouts
                fc_weekday_init_xpos += 133
                fc_pic_init_xpos += 133
                fc_temp_init_xpos += 133


# Signal handler for sigterm
def signal_term_handler(signal, frame):
    global epd
    logger.info("Got SIGTERM, stopping service and clean up")
    epd.Clear()
    epd.sleep()
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_term_handler)



###### Start up everything ###########

fetch_weather_info()
fetch_indoor_info()

# only need init once
epd.init()
epd.Clear()
# make the frame display Horizontal
Himage = Image.new('1', (epd.width, epd.height), 255)  # 255: clear the frame
draw = ImageDraw.Draw(Himage)

epaper_draw_layout_lines()
epaper_draw_clock()
epaper_draw_indoor_info()

if have_internet == True:
    epaper_draw_main_weather()
    epaper_draw_weather_warnings()
    epaper_draw_all_forecast()
else:
    # display text No internet
    draw.text((280, 255), str("No Internet!!"), font = font55, fill = 0)

epd.display(epd.getbuffer(Himage))


######### Loop starts here #####################################

# since there's no partially refresh for this 7.5" ePaper, therefore we have to
# draw everything.  It takes around 14 secs to refresh everything, so we offset
# 14 secs ahead
# 60-14 = 46
refreshTimeOffset = 46;
while True:
    try:
        now = datetime.datetime.now()

        # The logic explanation below

        # for every minute, update the clock and indoor temperature only
        if now.second == refreshTimeOffset:
            # since we're displaying "next min", we +1 min to the current time
            # as the displayTime

            ## THIS IS WRONG, FIX IT !!!!!!!!!!!!!!!!!!!!!
            #displayTime = now + datetime.timedelta(minutes=1)
            displayTime = datetime.datetime.now() + datetime.timedelta(minutes=1)

            logger.info("Display time is = %s", str(displayTime.minute))

            # only fetch weather info every 15 mins
            # when clock is xx:00, we also check if it's 00:00 and run the daily task
            if displayTime.minute == 0:
                #print('Start 15 min task - fetch weather info')
                logger.info("Start 15 min task")
                fetch_weather_info()
                # change the date and weekday in midnight
                if displayTime.hour == 0:
                    #print('Start daily task - change weekday')
                    logger.info("Start daily task in midnight.")
                    logger.info("Changing all date to next day")

                    # adding 1 min above won't make the time become next day
                    # gotta add next day manually
                    #displayTime = displayTime + datetime.timedelta(days=1)
                    mydate = displayTime.strftime("%d/%m/%Y")
                    mychi_day = chi_days[displayTime.weekday()]

            # for other times, just run the 15 min task
            if displayTime.minute == 15 or displayTime.minute == 30 or displayTime.minute == 45:
                logger.info("Start 15 min task")
                fetch_weather_info()

            # construct the time to display "next minute"
            #nextMinTime = datetime.time(now.hour, now.minute + 1)
            #mytime = nextMinTime.strftime("%H:%M")
            mytime = displayTime.strftime("%H:%M")

            Himage = Image.new('1', (epd.width, epd.height), 255)
            draw = ImageDraw.Draw(Himage)
            epaper_draw_clock()
            epaper_draw_layout_lines()
            epaper_draw_indoor_info()

            # Try to connect again every minute if we don't have internet before
            # we put this here to make sure we try to fetch the info before
            # we display the weather
            if have_internet == False:
                fetch_weather_info()

            # don't draw the weathers if we don't have have_internet
            # cause we don't have the data
            if have_internet == True:
                epaper_draw_main_weather()
                epaper_draw_weather_warnings()
                epaper_draw_all_forecast()
            else:
                # display text No internet
                draw.text((280, 255), str("No Internet!!"), font = font55, fill = 0)

            epd.display(epd.getbuffer(Himage))

        time.sleep(1)


    except KeyboardInterrupt:
        logging.info("Ctrl + c detected.  Shutdown and cleanup.")
        epd.Clear()
        epd.sleep()
        #epd7in5.epdconfig.module_exit()
        exit()
