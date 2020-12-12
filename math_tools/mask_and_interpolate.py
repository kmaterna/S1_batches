import numpy as np
import scipy.interpolate


def cut_grid(data, xbounds, ybounds, fractional=True, buffer_rows=3):
    # We express the desired bounds as either an index  or a fraction of the domain in that axis.
    # This is useful when we haven't decided on a resolution.
    # xbounds refer to columns
    # yowbounds refer to rows
    xmin = xbounds[0];
    xmax = xbounds[1];
    ymin = ybounds[0];
    ymax = ybounds[1];
    xmax_orig = np.shape(data)[1];
    ymax_orig = np.shape(data)[0];

    if fractional is True:
        xmin = int(xmin * xmax_orig)
        xmax = int(xmax * xmax_orig);
        ymin = int(ymin * ymax_orig);
        ymax = int(ymax * ymax_orig);

    # Defensive programming
    # I found a few columns of nans, so I'm protecting against them with buffer rows/cols.
    if xmin < buffer_rows:
        xmin = buffer_rows;
    if ymin < buffer_rows:
        ymin = buffer_rows;
    if xmax > np.shape(data)[1] - buffer_rows:
        xmax = np.shape(data)[1] - buffer_rows;
    if ymax > np.shape(data)[0] - buffer_rows:
        ymax = np.shape(data)[0] - buffer_rows;

    data_cut = data[ymin:ymax, xmin:xmax];

    print("Shape of the original data are: ", np.shape(data));
    print("Boundaries of the cut data are: ", ymin, ymax, xmin, xmax);
    print("Shape of the new data are: ", np.shape(data_cut));
    return data_cut;


def make_coherence_mask(cor, threshold):
    print("Making coherence mask.")
    mask = np.ones(np.shape(cor));
    for i in range(np.shape(cor)[0]):
        for j in range(np.shape(cor)[1]):
            if np.isnan(cor[i][j]) or cor[i][j] < threshold:
                mask[i][j] = np.nan;
    return mask;


def apply_coherence_mask(data, mask, is_complex=0, is_float32=False):
    # A future version of this function should probably check the type of the input data
    # and return the same type that came in.
    if is_float32 is False:
        if is_complex == 1:
            masked = np.complex64(np.multiply(data, mask));
        else:
            masked = np.float64(np.multiply(data, mask));
    else:
        if is_complex == 1:
            masked = np.complex32(np.multiply(data, mask));
        else:
            masked = np.float32(np.multiply(data, mask));
    return masked;


def interpolate_2d(data_array, is_complex=0):
    print("Performing 2d interpolation");
    if is_complex == 1:
        data_array = np.angle(data_array);

    ymax, xmax = np.shape(data_array);
    yarray = range(ymax);
    xarray = range(xmax);
    interpolated_values = np.zeros(np.shape(data_array));

    x_interps = [];
    y_interps = [];
    z_interps = [];
    xy_interps = [];
    xy_targets = [];

    # Time to get rid of the nan's.
    for i in range(len(yarray)):
        for j in range(len(xarray)):
            # xy_targets.append([xarray[j], yarray[i]]);
            # Get the real values for use in interpolating
            if not np.isnan(data_array[i][j]):
                x_interps.append(xarray[j]);
                y_interps.append(yarray[i]);
                xy_interps.append([xarray[j], yarray[i]]);
                z_interps.append(data_array[i][j]);
            # Collect the points where we interpolate
            else:
                xy_targets.append([xarray[j], yarray[i]]);

    # f = scipy.interpolate.interp2d(y_interps, x_interps, z_interps);
    z_targets = scipy.interpolate.griddata(xy_interps, z_interps, xy_targets, method='linear', fill_value=1);

    # Fill in the gaps using the interpolated value of z
    smoothdata = np.copy(data_array);
    for i in range(len(xy_targets)):
        idxx = xarray.index(xy_targets[i][0])
        idxy = yarray.index(xy_targets[i][1])
        if is_complex == 1:
            r = 1
            smoothdata[idxy][idxx] = np.cmath.rect(r, z_targets[i]);
        else:
            smoothdata[idxy][idxx] = z_targets[i];

    return smoothdata;
