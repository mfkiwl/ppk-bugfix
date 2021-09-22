"""
Subroutines to convert positoin between ECEF (earth-center,
earth-fixed) coodrinate, ENU (east-nourth-up) coordinate
and LLH (latitude,longitude and height)

- 2015.06.09 takeda Set return value double precision (not integer [0,0,0])
- 2015.01.25 takeda Change API
"""

from numpy import sin,cos,arctan2,sqrt,array,dot,deg2rad,rad2deg
from numpy import ndarray
from typing import List

__author__ = "Haruto Takeda <haruto.takeda@sony.com>"
__version__ = "1.2"

RE_WGS84 = 6378137.0 # radius of earth

def xyz2llh(p_xyz:list)-> List[float]:
    """
    Convert position in XYZ on ECEF to latitude,longitude, altitude.
    Args
    ----
    p_xyz[3]: x,y,z coordinate in ECEF [m]

    Returns
    -------
    p_llh[3]: position (latitude, longitude, altitude)
    """
    f = (1.0 / 298.257223563)  # flattening(WGS84)
    #(1.0/298.257222101) for  flattening of Geospatial Information Authority of Japan
    a = RE_WGS84  # radius of earth
    e = sqrt(f * (2.0 - f))
    b = a * (1.0 - f)

    h = a * a - b * b
    p = sqrt(p_xyz[0] * p_xyz[0] + p_xyz[1] * p_xyz[1])
    t = arctan2(p_xyz[2] * a, p * b)
    sint, cost = sin(t), cos(t)

    lat = arctan2(p_xyz[2] + h / b * sint * sint * sint, p - h / a * cost * cost * cost)
    n = a / sqrt(1.0 - e * e * sin(lat) * sin(lat))
    lon = arctan2(p_xyz[1], p_xyz[0])
    alt = (p / cos(lat)) - n
    return [lat, lon, alt]


def enuRxyz(base_lat:float, base_lon:float) -> ndarray:
    """
    ECEF座法系から観測値の局地推定座標系への回転行列.
    Rotation matrix from XYZ coordinate to Local Tanget Coordinate.

    Args
    ----
    base_lat:float, latitude in radian
    base_lon:float, longitude in radian

    Return
    ------
    R: ndarray, rotation matrix (p_enu = enuRxyz * p_xyz)
    """
    s1, c1 = sin(base_lon), cos(base_lon)
    s2, c2 = sin(base_lat), cos(base_lat)
    return array([\
        [     -s1,       c1, 0.0],
        [-c1 * s2, -s1 * s2, c2],
        [ c1 * c2,  s1 * c2, s2]])


def xyzRenu(base_lat, base_lon):
    """
    Calculate rotation matrix from enu to xyz coordinates.
    Args
    ----
    base_lat, base_lon: latitude and longitude [rad]
    """
    s1 = sin(base_lon)
    c1 = cos(base_lon)
    s2 = sin(base_lat)
    c2 = cos(base_lat)
    return array([\
        [-s1, -c1 * s2, c1 * c2],
        [ c1, -s1 * s2, s1 * c2],
        [0.0,       c2, s2]])


def xyz2enu(p_xyz, p_base_xyz, lat, lon):
    """ Convert position in XYZ coordinate to ENU coordinate

    Args
    ----
    p_xyz: ECEF X,Y,Z value [m]
    p_base_xyz: origin point in ECEF [m]

    Returns
    p_enu[3]: East-North-Up coordinate [m]
    """
    dx_xyz = array(p_xyz) - array(p_base_xyz)
    R  = enuRxyz(lat, lon)
    dx_enu = dot(R, dx_xyz)
    return dx_enu


def xyz2enu_old(p_xyz, p_base_xyz, base_lat, base_lon):
    x_df = p_xyz[0] - p_base_xyz[0]
    y_df = p_xyz[1] - p_base_xyz[1]
    z_df = p_xyz[2] - p_base_xyz[2]

    s1 = sin(base_lon)
    c1 = cos(base_lon)
    s2 = sin(base_lat)
    c2 = cos(base_lat)

    e = -x_df * s1 + y_df * c1
    n = -x_df * c1 * s2 - y_df * s1 * s2 + z_df * c2
    u = x_df * c1 * c2 + y_df * s1 * c2 + z_df * s2
    return [e, n, u]


def enu2xyz(p_enu, p_base_xyz, lat, lon):
    """
    <Args>
        enu_e, enu_n, enu_u: east, north, up [m]
        base_x,base_y,base_z: origin of ENU coorindate in ECEF
    <Returns>
        x,y,z: ECEF X,Y,Z value [m]
    """
    dx_xyz = dot(xyzRenu(lat, lon), p_enu)
    return p_base_xyz + dx_xyz


def llh2enu(p_geod, p_base_xyz, enuRxyz):
    '''Transform geodesic expression to ENU(east-north-up) cooridnate expression.
    <Args>
        p_geod[3] : target positon (latitude [rad], longitude [rad], altitude [m])
        p_base_goed[3]: base position
    <Returns>
        [e n u]: position in ENU coordinate [m]
    '''
    p_xyz = llh2xyz(p_geod)
    return dot(enuRxyz, array(p_xyz) - array(p_base_xyz))


def llh2xyz(p_geod):
    '''Coordinate transformation from geodesic expression to ECEF.
    <Args>:
       p_geoed[3]lat: latitude [rad], longitude[rad], altitude in meter [m]
    <Returns>:
       [x,y,z]: position in XYZ coordinate [m]
    '''
    f = (1.0 / 298.257223563)  # flattening(WGS84)
    a = 6378137.0  # radius of earth
    b, e = a * (1.0 - f), sqrt(f * (2.0 - f))
    n = a / sqrt(1.0 - e * e * sin(p_geod[0]) * sin(p_geod[0]))
    return [(n + p_geod[2]) * cos(p_geod[0]) * cos(p_geod[1]), 
            (n + p_geod[2]) * cos(p_geod[0]) * sin(p_geod[1]), 
            (n * (1.0 - e * e) + p_geod[2]) * sin(p_geod[0])]


def convStoD(decimal_num):
    num = decimal_num
    d = (int)(num)
    num = (num - d) * 60
    m = (int)(num)
    num = (num - m) * 60
    s = num
    return 10000 * d + 100 * m + s


def xyz2azel(sat, usr):
    '''
    Calculate azimuth and elevation of the target from given origin point.
    Args:
        sat[3]: satellite position on ECEF in meter
        usr[3]: receiver position  on ECEF in meter
    Returns:
        az,el:  and elevation in radian
    '''
    az=0.0
    el=pi/2.0

    usr_llh = xyz2llh(usr)
    if usr_llh[2]>-RE_WGS84:
        enu_e, enu_n, enu_u = xyz2enu(sat, usr, usr_llh[0], usr_llh[1])
        el = arctan2(enu_u, sqrt(enu_e * enu_e + enu_n * enu_n))
        az = arctan2(enu_e, enu_n)
    return [az, el]


def enu2azel(enu):
    el = arctan2(enu[2], sqrt(enu[0] * enu[0] + enu[1] * enu[1]))
    az = arctan2(enu[0], enu[1])
    return [az, el]


def xyz2los(sat, usr):
    """Transform ECEF to line-of-sign vector.
    Args:
        sat[3]: satellite position on ECEF [m]
        usr[3]: receiver position  on ECEF [m]
    Returns:
        [ex,ey,ez], r: line of sight vector in ECEF and distance
    """
    drs = sat - usr
    r = sqrt(sum(drs * drs))
    ex, ey, ez = drs[0] / r, drs[1] / r, drs[2] / r
    return [ex, ey, ez], r


def azel2los(az, el):
    """Line-of-sight is calculated from  and elevation.
    <Args>
    /elevation: angles in degree
    <Return>
    los[3]: line-of-sight vector in ENU coordinate. unit vector.
    """
    cosel = cos(el)
    e0 = sin(az) * cosel
    e1 = cos(az) * cosel
    e2 = sin(el)
    return array([e0, e1, e2])


def los2azel(los):
    """Convert line-of-sight vector in ENU coordinate into  and elevation.
    <Args>
    los[3]: line-of-sight vector inENU
    <Returns>
    [, elevation]:  and elevation in degree
    """
    e, n, u = los[0], los[1], los[2]
    az = arctan2(e, n)
    el = arctan2(u, sqrt(e * e + n * n))
    return [az, el]

#def enuRxyz(lat, lon):
#    """Calculate Rotation matrix from xyz to enu cordinates.
#    <Note>
#    Reference point of enu cordinate must be represented in XYZ coordinate.
#    """
#    R = xyzRenu(lat, lon)
#    return R.T


def _elevation(vec_enu):
    '''
    Calculate  and elevation of given vector in ENU coodinate.
    Note that returned value is angle in degree. 
    '''
    e,n,u = vec_enu[0], vec_enu[1], vec_enu[2]
    az = rad2deg( arctan2(e, n) ) # arctan2(Y=east, X=north)  of x
    #el = arcsin(u) * R2D
    el = rad2deg( arctan2(u, sqrt(e*e + n*n)) )
    return (az, el)


def pos_llh_str(pos_llh:list, sep_str = " ") -> str:
    return '{:.10f}'.format(rad2deg(pos_llh[0])) + sep_str + '{:.10f}'.format(rad2deg(pos_llh[1])) + sep_str + '{:.4f}'.format(pos_llh[2])
