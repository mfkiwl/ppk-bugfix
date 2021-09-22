"""
RTKLIBで用いられているPOSファイルを読み書きするためのプログラム.


"""
import xgnss.calc_time as calc_time
import xgnss.calc_xyz  as calc_xyz
from numpy import floor, deg2rad, rad2deg, sign, abs, sqrt, array
import datetime
from pandas import DataFrame, Series, to_datetime
from os import path


def load(pos_file:str, param = {}) -> list:
    '''
    Args
    ----
    pof_file: file path
    parms = {'date': 'utc' or 'gps', 'pos_type': 'llh' or 'xyz' or 'enu', 'base_pos_xyz': [x,y,z]}
    '''
    line_counter = 0
    pos_format = 'llh' # 0: llh, 1:enu, 2:xyz
    if 'base_pos_xyz' in param:
        p_base_xyz = param['base_pos_xyz']
    if 'pos_type' in param:
        pos_format = param['pos_type']
    #
    pos_epoch_list = []
    f = open(pos_file,encoding='shift-jis')
    while True:
        try:
            line = f.readline()
            if line[0] == '%':
                if line.find("baseline") > 0:
                    #print("ENU baseline format. Base position %f %f %f" % (pos0_geod_deg[0], pos0_geod_deg[1], pos0_geod_deg[2]) )
                    pos_format = 'enu'
                elif 'latitude' in line and 'longitude' in line and 'height' in line:
                    pos_format = 'llh'
                elif 'x-ecef' in line and 'y-ecef' in line and 'z-ecef' in line:
                    pos_format = 'xyz'
            else: break
        except Exception as e:
            print('rinex_pos.load: ',line)
            print(e)
            break
    #print('[rinex_pos.py] pos_format=%s' % pos_format)

    for line in f.readlines():
        line_counter = line_counter + 1
        if not line:
            break
        try:
            pos_epoch,is_valid = read_pos(line, pos_format)
            if is_valid: pos_epoch_list.append(pos_epoch)
        except Exception as e:
            print(e)
            pass
    return pos_epoch_list


def read_pos(line:str, pos_format):
    '''Parse one line of POS file in specific format.
    '''
    itm = line[:-1].split()
#00000000001111111111222222222233333333334444444444555555555566666666667777777777888888888899999999990000000000111111111122222222223333333333
#01234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789
#1920 351555.400  -3960659.8602   3355464.7457   3693777.7221   5   4  93.1565   9.3659 725.7939 -18.1492  22.2958-129.9897   0.00    0.0
#2016/09/21 00:54:34.000   35.333967246  139.490632689    45.4091   2   5   0.1892   0.2601   0.6699  -0.0244   0.3388  -0.2098   0.00    1.3
#2016/12/05 06:29:19.000  -3948624.9743   3387999.6798   3677017.0649   2   7   0.9985   0.9884   1.1171  -0.7814   0.7654  -0.8048   0.00    1.2

    if len(itm) < 14:
        print('ERROR! len ={len(itm)} < 14: ', itm)
        return None, False
    is_valid = True
    #
    # Read time
    #
    if itm[0].find('/') == 4 and itm[1].find(':') == 2:
        yy,mm,dd = int(itm[0][0:4]),int(itm[0][5:7]),int(itm[0][8:10])
        hr,mn,sc = int(itm[1][0:2]),int(itm[1][3:5]),float(itm[1][6:-1])
        t = calc_time.date2t(yy,mm,dd,hr,mn,sc)
        wk, tow = calc_time.t2gpstime(t)
    elif len(itm[0]) == 4:
        wk, tow = int(itm[0]), float(itm[1])
    pos_epoch = {'gpsweek':wk, 'gpstow': tow}
    yy,mm,dy,hr,mn,sc = calc_time.t2date(calc_time.gpstime2t(wk, tow))
    pos_epoch['datetime'] = datetime.datetime(yy,mm,dy,hr,mn, int(floor(sc)), int(1E6 * (sc - floor(sc))))

    #
    # Read position
    #
    x = []
    sdx,sdy,sdz,sdxy,sdeyz,sdzx = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    if pos_format == 'llh':
        lat,lon,hgt = float(itm[2]),float(itm[3]),float(itm[4])
        sdn,sde,sdu,sdne,sdeu,sdun = float(itm[7]),float(itm[8]),float(itm[9]),float(itm[10]),float(itm[11]),float(itm[12])
        x   = calc_xyz.llh2xyz([deg2rad(lat), deg2rad(lon), hgt])
        # TODO: !!!!!! covariance conversion !!!!!!!
        sdx,sdy,sdz,sdxy,sdeyz,sdzx = sdn,sde,sdu,sdne,sdeu,sdun
    elif pos_format == 'enu':
        enu_e,enu_n,enu_u = float(itm[2]),float(itm[3]),float(itm[4])
        sdn,sde,sdu,sdne,sdeu,sdun = float(itm[7]),float(itm[8]),float(itm[9]),float(itm[10]),float(itm[11]),float(itm[12])
        x = calc_xyz.enu2xyz(array([enu_e,enu_n,enu_u]))
        # TODO: !!!!!! covariance conversion !!!!!!
        sdx,sdy,sdz,sdxy,sdeyz,sdzx = sdn,sde,sdu,sdne,sdeu,sdun
    elif pos_format == 'xyz':
        x = float(itm[2]),float(itm[3]),float(itm[4])
        sdx,sdy,sdz,sdxy,sdeyz,sdzx = float(itm[7]),float(itm[8]),float(itm[9]),float(itm[10]),float(itm[11]),float(itm[12])
    else:
        is_valid = False

    pos_epoch['Q'], pos_epoch['nsat'] = int(itm[5]), int(itm[6])
    pos_epoch['X'], pos_epoch['Y'], pos_epoch['Z'] = x[0], x[1], x[2]
    pos_epoch['sdx'], pos_epoch['sdy'], pos_epoch['sdz'], pos_epoch['sdxy'], pos_epoch['sdyz'], pos_epoch['sdzx'] \
        = sdx, sdy, sdz, sdxy, sdeyz, sdzx
    #
    # Read additional
    #
    pos_epoch['age'],pos_epoch['ratio'] = float(itm[13]),float(itm[14])
    return pos_epoch, is_valid


def load_df(pos_file: path):
    """
    *.pos ファイル (主にRTKLIBの出力ファイル) を読んで pandas DataFrame を返す
    読み取りに失敗したら None を返す
    """
    try:
        pos_list = load(pos_file)
    except:
        return None
    if len(pos_list) == 0: # 
        return None
    df = DataFrame(index=arange(0, len(pos_list)), columns = ["datetime", "X", "Y", "Z", "Q", "nsat", "ratio", "age"])
    for i, v in enumerate(pos_list):
        for lb in ["datetime", "X", "Y", "Z", "Q", "nsat", "ratio", "age"]:
            df.loc[i, lb] = v[lb]
    #df = DataFrame(index=[], columns = ["datetime", "X", "Y", "Z", "Q", "nsat", "ratio", "age"])
    #for v in pos_list:
    #    df = df.append(Series([v['datetime'], v['X'], v['Y'], v['Z'], v['Q'], v['nsat'], v['ratio'], v['age']], index=df.columns), 
    #        ignore_index=True)
    df["datetime"] = to_datetime(df["datetime"], utc=True)
    return df

def write(pos_epoch_list, filepath, postype="llh"):
    f = open(filepath,'w')
    f.write('% (lat/lon/height=WGS84/ellipsoidal,Q=1:fix,2:float,3:sbas,4:dgps,5:single,6:ppp,ns=# of satellites)\n')
    if postype == "llh":
        f.write('%  GPST          latitude(deg) longitude(deg)  height(m)   Q  ns   sdn(m)   sde(m)   sdu(m)  sdne(m)  sdeu(m)  sdun(m) age(s)  ratio\n')
    elif postype == "xyz":
        f.write('%  GPST              x-ecef(m)      y-ecef(m)      z-ecef(m)   Q  ns   sdx(m)   sdy(m)   sdz(m)  sdxy(m)  sdyz(m)  sdzx(m) age(s)  ratio\n')
    for e in pos_epoch_list:
        str = get_epoch_str(e, postype)
        f.write(str)
        f.write("\n")
    f.close()


def value_bounded(v, v_min, v_max):
    '''
    Values are bounded with in v_min and v_max.
    '''
    if v < v_min:
        return v_min
    elif v > v_max:
        return v_max
    else:
        return v


def get_epoch_str(epoch, postype='llh'):
    """Generate string of one epoch positioning result in rinex pos format 
    Args:
    pos_type: expression type. Both 'llh' or 'xyz' is available
    """
    e = epoch
    if postype == "llh":
        if 'lat' in e and 'lon' in e and 'hgt' in e:
            lat, lon, hgt = e['lat'], e['lon'], e['hgt']
            pos_xyz = calc_xyz.xyz2llh([ deg2rad(lat),  deg2rad(lon), hgt])
        elif 'X' in e and 'Y' in e and 'Z' in e:
            pos_xyz = calc_xyz.xyz2llh([e['X'], e['Y'], e['Z']])
            pos_llh = calc_xyz.xyz2llh(pos_xyz)
            lat, lon, hgt = rad2deg(pos_llh[0]), rad2deg(pos_llh[1]), pos_llh[2]
        str = ""
        str = str + ('%4d' % int(e['gpsweek']))
        str = str + ('%11.3f' % e['gpstow'])
        str = str + ('%15.9f' % lat)
        str = str + ('%15.9f' % lon)
        str = str + ('%11.4f' % hgt)
        str = str + ('%4d'%e['Q'])
        str = str + ('%4d'%e['nsat'])
        if 'sdn' in e and 'sde' in e and 'sdu' in e and 'sdne' in e and 'sdeu' in e and 'sdun' in e:
            sdn, sde, sdu, sdne, sdeu, sdun = e['sdn'], e['sde'], e['sdu'], e['sdne'], e['sdeu'], e['sdun']
        elif 'cvx' in e and 'cvy' in e and 'cvz' in e and 'cvxy' in e and 'cvyz' in e and 'cvzx' in e:
            Q_enu = calc_xyz.xyzRenu(pos_xyz)
            sdx, sdy, sdz = sqrt(e['cvx']), sqrt(e['cvy']), sqrt(e['cvz'])
            sdxy, sdyz, sdzx = sign(e['cvxy']) * sqrt(abs(e['cvxy'])), sign(e['cvyz']) * sqrt(abs(e['cvyz'])), sign(e['cvzx']) * sqrt(abs(e['cvzx']))
        elif 'sdx' in e and 'sdy' in e and 'sdz' in e and 'sdxy' in e and 'sdyz' in e and 'sdzx' in e:
            sdx, sdy, sdz, sdxy, sdyz, sdzx = e['sdx'], e['sdy'], e['sdz'], e['sdxy'], e['sdyz'], e['sdzx']
            Q_enu = calc_xyz.xyzRenu(pos_xyz)

        str = str + ('%9.4f' % value_bounded(sdn, -99.0, 99.0))
        str = str + ('%9.4f' % value_bounded(sde, -99.0, 99.0))
        str = str + ('%9.4f' % value_bounded(sdu, -99.0, 99.0))
        str = str + ('%9.4f' % value_bounded(sdne, -99.0, 99.0))
        str = str + ('%9.4f' % value_bounded(sdeu, -99.0, 99.0))
        str = str + ('%9.4f' % value_bounded(sdun, -99.0, 99.0))
        str = str + ('%7.2f' % e['age'])
        str = str + ('%7.1f' % e['ratio'])
    elif postype == "xyz":
#  01234567890123401234567890123401234567890123401230123012345678012345678012345678012345678012345678012345678
#00  -3976219.2317   3382373.0986   3652513.1387   5   7   4.1381   5.0455   4.0742  -4.0397   3.4676  -3.0181   0.00    0.0
        #print(e)
        if 'sdx' in e and 'sdy' in e and 'sdz' in e and 'sdxy' in e and 'sdyz' in e and 'sdzx' in e:
            sdx, sdy, sdz, sdxy, sdyz, sdzx = e['sdx'], e['sdy'], e['sdz'], e['sdxy'], e['sdyz'], e['sdzx']
        elif 'cvx' in e and 'cvy' in e and 'cvz' in e and 'cvxy' in e and 'cvyz' in e and 'cvzx' in e:
            sdx, sdy, sdz = sqrt(e['cvx']), sqrt(e['cvy']), sqrt(e['cvz'])
            sdxy, sdyz, sdzx = sign(e['cvxy']) * sqrt(abs(e['cvxy'])), sign(e['cvyz']) * sqrt(abs(e['cvyz'])), sign(e['cvzx']) * sqrt(abs(e['cvzx']))
        str = ""
        str = str + ('%4d' % int(e['gpsweek']))
        str = str + ('%11.3f' % e['gpstow'])
        str = str + ('%15.4f' % e['X'])
        str = str + ('%15.4f' % e['Y'])
        str = str + ('%15.4f' % e['Z'])
        str = str + ('%4d' % e['Q'])
        str = str + ('%4d' % e['nsat'])
        str = str + ('%9.4f' % value_bounded(sdx, -99.0, 99.0))
        str = str + ('%9.4f' % value_bounded(sdy, -99.0, 99.0))
        str = str + ('%9.4f' % value_bounded(sdz, -99.0, 99.0))
        str = str + ('%9.4f' % value_bounded(sdxy, -99.0, 99.0))
        str = str + ('%9.4f' % value_bounded(sdyz, -99.0, 99.0))
        str = str + ('%9.4f' % value_bounded(sdzx, -99.0, 99.0))
        str = str + ('%7.2f'%e['age'])
        str = str + ('%7.1f'%e['ratio'])
#    str = str + ('\n')
    return str


def GetENUPos(pos_epoch_list, origin_pos_geod):
#def GetENUPos(pos_epoch_list, origin_pos_geod, pos_format="llh"):
    """
    <Args>
    pos_epoch_list :
    origin_pos_geod[3]: latitude[deg], longitude[deg], height[m]
    <Return>
    """
    tidx, dat, Q = [], [], []
    #if pos_fomrat == "enu":
    #    for e in pos_epoch_list:
    #        dat.append(e["lat"],e["lon"],e["hgt"]))
    #        tidx.append(e["gpstow"])
    #        Q.append(e["Q"])
    p_base_geod    = [deg2rad(origin_pos_geod[0]), deg2rad(origin_pos_geod[1]), origin_pos_geod[2]]
    for e in pos_epoch_list:
        if 'lat' in e:
            p_geod = [deg2rad(e["lat"]), deg2rad(e["lon"]), e["hgt"]]
            Q.append(e["Q"])
            x = calc_xyz.blh2enu(p_geod, p_base_geod)
            dat.append(x)
        else:
            x = calc_xyz.xyz2enu([e['X'],e['Y'],e['Z']], p_base_geod)
            Q.append(e["Q"])
            dat.append(x)
        tidx.append(e["gpstow"])

    dat  = array(dat)
    tidx = array(tidx) - tidx[0]
    return tidx, dat, Q

