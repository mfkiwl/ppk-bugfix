"""
Time expression conversion

(C) Sony Corporation 2015, Aerosense 2021
"""

__version__ = "0.1"
__date__    = "21 Apr 2015"

from datetime import datetime, timezone

TIME_T_ORIGIN = 315964800 # 1980,Jan,6, 00:00:00
SECONDS_WEEK =  3600*24*7

def gpstime2t(wk: int, tow: float) -> float:
    """ Convert GPS week number and time of week to Unix time.
    GPS週番号と週時刻からUNIX時間に変換する。

    Args
    ----
        wk  : GPS week (0 is the week of 1980,Jan,06)
        tow : time of week in second
    return
    ------
        t : LINUX time in second
    """
    return wk * SECONDS_WEEK + tow + TIME_T_ORIGIN


def t2gpstime(t: float):
    """ Convert time to GPS week and time of week.
    UNIX時間を週番号と週時刻に変換する。

    Input
    -----
        t : LINUX time

    Returns
    -------
        gpsweek : GPS week (0 is the week of 1980,Jan,06)
        sec_of_week : second in the week
    """
    tow = (t - TIME_T_ORIGIN)%SECONDS_WEEK
    return [int((t - TIME_T_ORIGIN - tow)/SECONDS_WEEK), tow]


def gpstime2datetime(wk:int, tow:float):
    """
    GPS週番号と週秒を datetime.datetime に変換する
    """
    return datetime.utcfromtimestamp(wk * SECONDS_WEEK + tow + TIME_T_ORIGIN)


def t2date(t: float):
    """ Convert time to calender date
    args:
    t : LINUX time
    return:
    yy,mm,dd,hr,mn,ss : calendar time
    """
    t_sec_frac = t % 1
    tm_strc = datetime.utcfromtimestamp(t)
    yy = tm_strc.year
    mm = tm_strc.month
    dd = tm_strc.day
    hr = tm_strc.hour
    mn = tm_strc.minute
    ss = tm_strc.second + t_sec_frac
    return [yy, mm, dd, hr, mn, ss]


def t2date_str(t: float):
    """ Convert time to text string. UNIX時刻を年月日時分秒の文字列に変換する。

    Input
    -----
        t: Linux time [s]
    Returns
    -------
        date_str:str, string of the time in YYYY/MM/DD hr:mn:sec
    """
    yy,mm,dd,hr,mn,ss = t2date(t)
    return "%4d/%02d/%02d %02d:%02d:%06.3f" % (yy,mm,dd,hr,mn,ss)


def gpstime2date_str(wk: int, tow: float):
    """
    Input
    -----
        wk: week number
        tow: time of week
    """
    t = gpstime2t(wk, tow)
    return t2date_str(t)


def date2t(yy: int, mm: int, dd: int, hr: int, mn: int, sec: float):
    """ Convert calender time to time
    Input
    -----
    yy year
    mm month
    dd day
    hr hour
    mn minutes
    sec second
    """
    sec_int = int(sec)
    sec_frac = sec % 1
    return datetime(yy,mm,dd,hr,mn,sec_int,int(1000000*sec_frac)).timestamp()
    #ts = calendar.timegm(dt.timetuple()) + sec_frac

def t2doy(t):
    '''converts time to day of year
    args:
        t : LINUX time
    return:
        doy : day of year (days)
    '''
    ep = t2date(t)
    t1 = date2t(ep[0],ep[1],ep[2],ep[3],ep[4],ep[5])
    ep[1] = ep[2] = 1
    ep[3] = ep[4] = ep[5] = 0
    t2 = date2t(ep[0],ep[1],ep[2],ep[3],ep[4],ep[5])
    doy = (t1-t2)/86400.0+1.0
    return doy


def t2mjd(t):
    '''converts time to modified Julian date
    args:
        t : LINUX time
    return
        mjd : modified Julian date
    '''
    t0 = date2t(1858,11,17,0,0,0)
    return (t-t0)/86400.0


def t2year(t):
    '''
    converts time to year
    Args
    ----
        t : LINUX time
    Return
    ------
        yy : year
    '''
    tm_strc = datetime.utcfromtimestamp(t)
    yy = tm_strc.year
    t0 = date2t(yy,1,1,0,0,0)
    t1 = date2t(yy+1,1,1,0,0,0)
    yy += float(t-t0)/float(t1-t0)
    return yy
