"""
PPKを実行し、カメラの撮像位置を求める計算を実行する.

"""

from datetime import datetime, timedelta, timezone
from pandas import DataFrame, Series
from numpy import nan, array, rad2deg, sqrt
from os import environ
from logging import getLogger
from typing import Tuple
from subprocess import STDOUT, Popen, PIPE

## 内製ライブラリ..
import xgnss.rinex_pos as rnx_pos
from xgnss.calc_xyz import xyz2llh, enu2xyz
### RTKLIBの後処理測位計算プログラム.
POS_ACC_MIN = 0.030
POST_RTKLIB_EXE = "rnx2rtkp" # Must be in $PATH
RTKLIB_TEMPLATE_FILE = environ.get("PPK_EXTDIR", ".") + "/ext/rtklib/data/template-rnx2rtkp-conf.txt"

TIME_T_ORIGIN = 315964800 # 1980,Jan,6, 00:00:00
RE_WGS84 = 6378137.0   # radius of earth

_logger = getLogger(__name__)

from os import path,fsync
def _create_conffile(template_conffile:str, out_conffile:str, rov_info:dict, ref_info:dict, **kwargs):
    all_lines = open(template_conffile)
    navsys = 1 # (1:gps+2:sbas+4:glo+8:gal+16:qzs+32:comp)
    if kwargs.get("use_glonass", False):
        navsys += 4
    if kwargs.get("use_galileo", False):
        navsys += 8
    if kwargs.get("use_qzss", False):
        navsys += 16
    if kwargs.get("use_compass", False):
        navsys += 32
    _elmask = kwargs.get("elmask", 25.0)
    exclude_prns = ""
    if "exclude_sats" in kwargs:
        exclude_prns = " ".join( kwargs["exclude_sats"])
    _ant_file = path.dirname(path.abspath(template_conffile)) + "/JSIM_ANT.001"
    if not path.exists(_ant_file):
        _ant_file = ""
    arg = "off" #"autocal" #"off"
    if rov_info["rcv"] == ref_info["rcv"]:
        arg = "on"
    v = kwargs.get('snrmask', 38) #40?
    _rtklib_snmask = "{},{},{},{},{},{},{},{},{}".format(v, v, v, v, v, v, v, v, v)
    _rov_ant_d = rov_info.get("ant_d", [0.0, 0.0, 0.0])
    _ref_ant_d = ref_info.get("ant_d", [0.0, 0.0, 0.0])
    rtklib_params \
        = {"__POSMODE__": kwargs.get("posmode", "static"),
            "__ROVER_FREQUENCY__": kwargs.get("freq", "l1"),
            "__SOL_TYPE__": kwargs.get("sol_filter_type", "combined"),
            "__ELMASK__": _elmask,
            "__SNMASK__": _rtklib_snmask,
            "__EXSATS__": exclude_prns,
            "__NAVSYS__": navsys,
            "__AR_MODE__": kwargs.get("armode", "continuous"),
            "__GAR__": arg,
            "__BAR__": kwargs.get("bdsarmode", "off"),
            "__MAXAGE__": kwargs.get("maxage", 10.0),
            "__BASE_LATITUDE__": ref_info["lat"],
            "__BASE_LONGITUDE__": ref_info["lon"],
            "__BASE_ALTITUDE__": ref_info["ellipsed_alt"],
            "__ANT1_TYPE__": rov_info.get("ant", "no_antenna_info"),
            "__ANT1DE__": _rov_ant_d[0],
            "__ANT1DN__": _rov_ant_d[1],
            "__ANT1DU__": _rov_ant_d[2],
            "__ANT2_TYPE__": ref_info.get("ant", "no_antenna_info"),
            "__ANT2DE__": _ref_ant_d[0],
            "__ANT2DN__": _ref_ant_d[1],
            "__ANT2DU__": _ref_ant_d[2],
            "__ANT_FILE__": _ant_file}
    for k, v in rtklib_params.items():
        all_lines = [ l.replace(k, str(v)) for l in all_lines]
    print("out_conffile=",out_conffile)
    with open(out_conffile, "w") as f:
        for l in all_lines:
            f.write(l)
        f.flush()
        fsync(f.fileno())
        return True
    return False

def _load_dji_timestamp_mrk(mrk_file:str) -> list:
    """
    Read DJI RTK drone's *Timestamp.MRK file
    Args
    ----
    mrk_file:path, input file path

    Returns
    -------
    data:list, time stamp data (picture id, dx(DNU coordiate), llh, datetime)
    """
    dat = []
    with open(mrk_file) as f:
        lines = f.readlines()
        for l in lines:
            if l[0] == "#":
                continue
            # read line of normal *Timestamp.MRK format
            v = [ s for s in l.split("\t") if s != '']
            if len(v) <= 8:
                break
            pic_id = int(v[0])
            tow, wk = float(v[1]), int(v[2].replace("[","").replace("]",""))
            t = datetime.fromtimestamp(wk * 3600*24*7 + tow + TIME_T_ORIGIN, tz=timezone.utc)
            dx= [float(v[3+i].split(",")[0]) * 1E-3 for i in range(3) ]
            p_llh = [float(v[6+i].split(",")[0]) for i in range(3) ]
            dat.append({"pic_id":pic_id, "dx": dx, "llh": p_llh, "datetime":t})
    return dat


def geotag_info_from_posfile_and_mrkfile(posfile:str, mrkfile:str, photo_basename:str, **kwargs) \
    -> Tuple[DataFrame, dict]:
    """
    POSファイルと *Timestamp.MRK ファイルを読んで、JPGファイル名と位置のリストを作成する。

    Parameters
    ----------
    posfile, RTKLIB output(*.pos)
    mrkfile, DJI time stamp of PPK files(*Timestamp.MRK)
    photo_basename, photo files is refered by photo_basenameXXXX where XXXX is incrementing number.
    **kwargs, options
    shutter_timelag, time delay of camera shutter from recorded time (milli-second)

    Returns
    -------
    df_imgs, DataFrame of image geotag
    ppk_options, options loaded from input files
    """

    # input data
    posdata = rnx_pos.load(posfile)
    print("pos: {} ({})".format(posfile, len(posdata)))
    mrkdat = _load_dji_timestamp_mrk(mrkfile)
    print("mrk: {} ({})".format(mrkfile, len(mrkdat)))
    print("photo_baseaname={}".format(photo_basename))
    if len(posdata) > 0:
        print("GPS data: ", posdata[0]["datetime"].isoformat(), " --- ", posdata[len(posdata)-1]["datetime"].isoformat())
    else:
        raise("Input PPK result position is empty.")
    if len(mrkdat) > 0:
        print("MRK data: ", mrkdat[0]["datetime"].isoformat(), " --- ", mrkdat[len(mrkdat)-1]["datetime"].isoformat())
    else:
        raise("Input Timestamp is empty")

    def _find_close_epoch(t_in:datetime, posdata:list):
        """
        """
        for i in range(len(posdata)-1):
            d1 = posdata[i]["datetime"]
            d2 = posdata[i+1]["datetime"]
            dt1 =  (t_in - d1).total_seconds()
            dt2 =  (d2 - t_in).total_seconds()
            if dt1 > 0.0 and dt2 > 0.0:
                return  i, i+1, dt1, dt2
        return len(posdata)-1, None, nan, nan

    df_imgs = DataFrame( index=[], columns=["name", "datetime", "lat", "lon", "hgt", "north_acc", "east_acc", "up_acc"] )
    shutter_timelag = kwargs.get("shutter_timelag", 0.0)
    #shutter_timelag = ppk_options.get("shutter_timelag", shutter_timelag)
    #data_name = path.splitext( path.basename(mrkfile) )[0][:-4]
    #photo_basename = "{}_{}".format( path.basename(mrkfile).split("_")[0], path.basename(mrkfile).split("_")[1] )
    for d in mrkdat:
        i1, i2, dt1, dt2 = _find_close_epoch(d['datetime'] - timedelta(seconds=shutter_timelag), posdata)
        if i1 is None or i2 is None:
            continue
        c1, c2 = dt2 / (dt1 + dt2), dt1 / (dt1 + dt2)
        ## Interpolation of 2 points
        p1_xyz = array( [ posdata[i1]["X"], posdata[i1]["Y"], posdata[i1]["Z"] ] )
        p2_xyz = array( [ posdata[i2]["X"], posdata[i2]["Y"], posdata[i2]["Z"] ] )
        p_xyz = c1 * p1_xyz + c2 * p2_xyz
        p_llh = xyz2llh(p_xyz)
        ## Compensation vector
        dx_enu = [d['dx'][1], d['dx'][0], -d['dx'][2]] # enu to ned
        p_img_xyz = enu2xyz(dx_enu, p_xyz, p_llh[0], p_llh[1])
        p_img_llh = xyz2llh(p_img_xyz)
        ## Position Accuracy
        p1_sig_enu = array( [ posdata[i1]["sdx"], posdata[i1]["sdy"], posdata[i1]["sdz"] ] )
        p2_sig_enu = array( [ posdata[i2]["sdx"], posdata[i2]["sdy"], posdata[i2]["sdz"] ] )
        sig_dx_enu = [ max(sqrt( (c1*p1_sig_enu[i])**2 + (c2*p2_sig_enu[i])**2 ), POS_ACC_MIN) for i in range(0, 3)]
        pic_name = photo_basename + "{:04d}".format(int(d["pic_id"])) + kwargs.get("postfix","")
        df_imgs = df_imgs.append(Series([pic_name, d['datetime'] - timedelta(seconds=shutter_timelag),\
                        rad2deg(p_img_llh[0]), rad2deg(p_img_llh[1]), p_img_llh[2],\
                        sig_dx_enu[0], sig_dx_enu[1], sig_dx_enu[2]], \
                    index=df_imgs.columns), \
                ignore_index=True)
    for k in ["lat","lon"]:
        df_imgs[k] = df_imgs[k].map(lambda x: '{0:.8f}'.format(x))
    for k in ['hgt', "north_acc", "east_acc", "up_acc"]:
        df_imgs[k] = df_imgs[k].map(lambda x: '{0:.4f}'.format(x))
    df_imgs = df_imgs.sort_values(by="name")
    return df_imgs


def camera_geotagging_by_ppk(drone_rinex_file:str, ref_rinex_file:str, nav_rinex_file:str, ref_info:dict,\
                            timestamp_file:str, photo_basename:str, **kwds):
    """
    PPKの測位計算を実行し、入力した時刻の位置とアンテナ〜カメラ補正情報を適用してカメラ位置を求める.

    Parameters
    ----------
    drone_rinex_file, ドローンのRINEX file(GNSS raw measurement)
    ref_rinex_file, 基準局のRINEX file
    nav_rinex_file, 衛星軌道情報のRINEX file
    ref_dict, 基準局情報を格納したdictionary (TODO: 引数にする)
    timestampfile, タイムスタンプファイル
    photo_basename, 写真ファイルのbase name

    Returns
    -------
    df, 各写真のカメラ位置を格納した DataFrame
    params,
    """
    work_dir = kwds.get("work_dir", ".")
    rtklib_conffile = "{}/ppk.conf".format(work_dir)
    _out_posfile = "{}/out.pos".format(work_dir)
    rov_info = {"rcv": ""}
    _create_conffile(RTKLIB_TEMPLATE_FILE, rtklib_conffile, rov_info, ref_info, \
        use_glonass = True, use_galileo = True, use_qzss = True, use_compass = True, \
        posmode = "kinematic", freq="l1+l2", armode="fix-and-hold", elmask=15, maxage=30.0, snrmask=30)
#        posmode = "kinematic", freq="l1+l2", elmask=25, maxage=30.0, snrmask=33)

    cmd_str = "{post_rtk_exe} -k {conffile} {rov} {ref} {nav} -o {pos}".format(post_rtk_exe=POST_RTKLIB_EXE, \
            conffile = rtklib_conffile, \
            rov= drone_rinex_file, ref=ref_rinex_file, nav= nav_rinex_file, \
            pos=_out_posfile, snrmask=30)
    _logger.info("({}) cmd={}".format(__name__, cmd_str))
    try:
        p = Popen(cmd_str.split(" "), stdout=PIPE, stderr=PIPE)
        _stdout, _stderr = p.communicate()
        _st = p.wait()
    except Exception as e:
        print("({}) Exception {}".format(__name__, e))
        raise

    # TimeStampファイルをもとにアンテナカメラ補正、PPKの結果を時刻変換してカメラ位置を求める.
    _logger.info("Load {} and compensate camera-antenna position".format(timestamp_file))
    df = geotag_info_from_posfile_and_mrkfile(_out_posfile, timestamp_file, photo_basename, postfix=kwds.get("postfix",""))

    return df

from os import makedirs
def main(args:dict):
    global RTKLIB_TEMPLATE_FILE
    RTKLIB_TEMPLATE_FILE = args.rtklib_template_file
    global POST_RTKLIB_EXE
    POST_RTKLIB_EXE = \
        environ.get("MGNSS_EXTDIR", ".") \
        + "/ext/rtklib_2.4.3_b34/app/consapp/rnx2rtkp/gcc/rnx2rtkp"
    if not path.isfile(POST_RTKLIB_EXE):
        print("ERROR: rtklib application (rnx2rtkp) is not prepared.")
        return -1
    # 作業用フォルダを作成.
    _ppk_dir = "ppk_proc"
    makedirs(_ppk_dir, exist_ok=True)
    # 基準局の情報
    _pos = [ float(v) for v in args.relpos.split(",")]
    ref_info = {'obsfile': args.ref_rnx_obs,
            "lat":_pos[0], "lon":_pos[1], "ellipsed_alt":_pos[2],
            'ant': "",
            'ant_d': [0.0,0.0,0.0],
            'rcv': "",
            'dist3d': 0.0}
    # 実行
    df = camera_geotagging_by_ppk(\
        args.rnx_obs, \
        args.ref_rnx_obs, \
        args.rnx_nav, \
        ref_info,\
        args.timestamp_file,
        args.photo_file_prefix, work_dir=_ppk_dir, postfix=args.photo_file_postfix)
    df.to_csv(args.out, index=False)
    print("out:{} ({})".format(args.out, len(df)))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog= "PPK camera geotagging "
    )
    parser.add_argument("rnx_obs", help="RINEX observation file (*.obs)", type=str)
    parser.add_argument("rnx_nav", help="RINEX navigation file (*.nav)", type=str)
    parser.add_argument("ref_rnx_obs", help="RINEX observation file of reference station (*.obs)", type=str)
    parser.add_argument("timestamp_file", help="Camera offset file in DJI PPK file format (*.MRK)", type=str)
    parser.add_argument("relpos", help="Reference station position (e.g., 35.657204659,140.048099674,43.7597)", type=str)
    parser.add_argument("--out", help="output camera position CSV file", default="camera_ref.csv")
    parser.add_argument("--photo_file_prefix", help="photo file prefix", default="image_0001_", type=str, required=False)
    parser.add_argument("--photo_file_postfix", help="photo file prefix", default=".JPG", type=str, required=False)
    parser.add_argument("--rtklib_template_file", help="template of RTKLIB conf file", \
        default="conf/template-rnx2rtkp-conf.txt", type=str, required=False)
    args = parser.parse_args()
    main(args)
