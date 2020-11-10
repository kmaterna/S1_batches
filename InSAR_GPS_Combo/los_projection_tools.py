# A few functions that help project into and out of LOS
# Mostly trig
# Example: 
# Dlos = [U_n sin(phi) - U_e cos(phi)]*sin(lamda) + U_u cos(lamda)
# [U_e, U_n, U_u] are the east, north, and up components of the deformation. 
# phi   = azimuth of satellite heading vector, positive clockwise from north.
# lamda = local incidence angle at the reflector.
# from Fialko et al., 2001. 

import numpy as np
import collections


Velfield = collections.namedtuple("Velfield", ['name', 'nlat', 'elon', 'n', 'e', 'u', 'sn', 'se', 'su', 'first_epoch',
                                               'last_epoch']);
# A useful structure to hold GPS velocity fields and their LOS-projected versions
# In the LOS-projected case, we use 'e' as the LOS velocity and the other columns are zeros
# Meant to be used in a list of these objects (one for each station)


def closest_index(lst, K):
    # Given list lst, and target K, which element is closest?
    index = min(range(len(lst)), key=lambda i: abs(lst[i] - K));
    deg_distance = lst[index] - K;
    return index, deg_distance;


def simple_project_ENU_to_LOS(U_e, U_n, U_u, flight_angle, incidence_angle):
    # Dlos = [U_n sin(phi) - U_e cos(phi)]*sin(lamda) + U_u cos(lamda)
    # [U_e, U_n, U_u] are the east, north, and up components of the deformation.
    # phi   = azimuth of satellite heading vector, positive clockwise from north.
    # lamda = local incidence angle at the reflector (usually angle from the vertical).
    # Fialko 2001
    # Works for single values and for 1D arrays of all arguments

    if np.size(U_e) > 1:  # processing a 1D array of values
        if np.size(flight_angle) == 1:
            phi = [np.deg2rad(flight_angle) for x in U_e];  # bumping up the flight and incidence angles into 1D arrays
            lamda = [np.deg2rad(incidence_angle) for x in U_e];  # otherwise, we assume they are matched 1D arrays
        else:
            phi = [np.deg2rad(x) for x in flight_angle];  # 1D arrays of angles in radians nows
            lamda = [np.deg2rad(x) for x in incidence_angle];
        d_los = [0 * i for i in U_e];
        for i in range(len(U_e)):
            d_los[i] = ((U_n[i] * np.sin(phi) - U_e[i] * np.cos(phi)) * np.sin(lamda) + U_u[i] * np.cos(lamda));

    else:  # processing a single value
        phi = np.deg2rad(flight_angle);
        lamda = np.deg2rad(incidence_angle);
        d_los = (U_n * np.sin(phi) - U_e * np.cos(phi)) * np.sin(lamda) + U_u * np.cos(lamda);

    return d_los


def get_point_enu_interp(reference_point, f_east=None, f_north=None, f_up=None):
    # Useful for reference points, for example
    # reference point is [lon, lat]
    # Interpolated functions are required if the reference isn't located at a gps station.
    velref_e = f_east(reference_point[0], reference_point[1]);
    velref_n = f_north(reference_point[0], reference_point[1]);
    if f_up is None:
        velref_u = 0;
    else:
        velref_u = f_up(reference_point[0], reference_point[1]);
    return velref_e, velref_n, velref_u;


def get_point_enu_veltuple(vel_tuple, reference_point_coords=None, reference_point_name=None, zero_vertical=False):
    # If the reference is co-located with a GPS station, we find it within the tuple.
    # We either use name or lat/lon
    if reference_point_name is not None:
        for station_vel in vel_tuple:
            if station_vel.name == reference_point_name:
                velref_e = station_vel.e;
                velref_n = station_vel.n;
                if zero_vertical:
                    velref_u = 0;
                else:
                    velref_u = station_vel.u;
                reflon = station_vel.elon;
                reflat = station_vel.nlat;
        return velref_e, velref_n, velref_u, reflon, reflat;
    else:
        for station_vel in vel_tuple:
            if station_vel.elon == reference_point_coords[0] and station_vel.nlat == reference_point_coords[1]:  # should I make these tolerances?
                velref_e = station_vel.e;
                velref_n = station_vel.n;
                if zero_vertical:
                    velref_u = 0;
                else:
                    velref_u = station_vel.u;
        return velref_e, velref_n, velref_u;


def paired_gps_geocoded_insar(gps_los_velfield, xarray, yarray, LOS_array, window_pixels=5):
    # A function to extract the paired LOS InSAR and GPS velocities
    # at pixels given by lons/lats in gps_los_velfield
    # It averages over a window of pixels whose width is given by an input parameter
    # It only returns non-nan values
    insar_los_array = [];
    gps_los_array = [];
    distance_tolerance = 0.01;  # degrees (approximately 1 km)
    for station_vel in gps_los_velfield:
        xi, deg_distance_x = closest_index(xarray, station_vel.elon);
        yi, deg_distance_y = closest_index(yarray, station_vel.nlat);
        if deg_distance_x < distance_tolerance and deg_distance_y < distance_tolerance:
            target_array = LOS_array[yi - window_pixels:yi + window_pixels, xi - window_pixels:xi + window_pixels]
            # default tolerance is about 1 km, and it shows whether or not we are accidentally outside of the InSAR domain
            InSAR_LOS_value = np.nanmean(target_array);
            if ~np.isnan(InSAR_LOS_value):
                insar_los_array.append(InSAR_LOS_value);
                gps_los_array.append(station_vel.e);  # the LOS velocity
    return np.array(insar_los_array), np.array(gps_los_array);


# A little bit of IO for working with GPS velocity fields in LOS geometries
# -------------------------------- # 
def input_gps_as_los(filename):
    print("Reading file %s " % filename);
    gps_velfield = [];
    [elon, nlat, los_vel, name] = np.loadtxt(filename, usecols=(0, 1, 5, 6), unpack=True,
                                             dtype={'names': ('elon', 'nlat', 'los_vel', 'station_name'),
                                                    'formats': (np.float, np.float, np.float, 'U4')});
    for i in range(len(elon)):
        gps_station_as_los = Velfield(name=name[i], elon=elon[i], nlat=nlat[i], e=los_vel[i], n=0, u=0, se=0,
                            sn=0, su=0, first_epoch=0, last_epoch=0);
        gps_velfield.append(gps_station_as_los);
    return [gps_velfield];


def output_gps_as_los(gps_velfield, LOS_velfield, outfile):
    ofile = open(outfile, 'w');
    for i in range(len(LOS_velfield)):
        ofile.write("%f %f %f %f %f %f %s \n" % (
        LOS_velfield[i].elon, LOS_velfield[i].nlat, gps_velfield[i].e, gps_velfield[i].n, gps_velfield[i].u,
        LOS_velfield[i].e, LOS_velfield[i].name));
    ofile.close();
    print("-->Outputs printed to %s" % outfile);
    return;
