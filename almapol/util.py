from urllib import request
from datetime import datetime
import io
import numpy as np
import xml.etree.ElementTree as ET

BAND_TO_HZ = {
    "3" : 97.5e9,
    'band3': 97.5e9,
    '3mm': 97.5e9,
    '6':179e9,
    'band6':179e9,
    '6mm':179e9
}

def check_var(varname):
    try:
        exec(varname)
    except NameError as exc:
        raise NameError(f"Missing {varname} from your config file!") from exc

def parse_votable(votable_path):
    tree = ET.parse(votable_path)
    root = tree.getroot()

    # Everything is under the "TABLE" key so we can treat that as a "root"
    table = root.find("./RESOURCE/TABLE")

    # get the field names
    fields = [element.attrib["name"] for element in table.findall("FIELD")]
    
    # extract the data corresponding to each of these fields
    data = []
    for tr in table.findall("./DATA/TABLEDATA/TR"):
        row = []
        for td in tr.findall("TD"):
            row.append(td.text)
        data.append(row)

    # package this data into a dictionary of numpy arrays
    packaged_data = {f:np.array(d) for f,d in zip(fields,list(zip(*data)))}

    float_keys = ["FluxDensity", "FluxDensityError", "SpectralIndex", "SpectralIndexError", "Frequency"]
    for k in float_keys:
        packaged_data[k] = packaged_data[k].astype(float)

    return packaged_data    

def get_recent_fcal_flux(date, band_name, Fcal_name):
    try:
        spix_q = BAND_TO_HZ[band_name]
    except KeyError:
        raise KeyError(f"{band_name} not in util.BAND_TO_HZ dictionary mapping! Please add it!")

    url = f"https://almascience.nrao.edu/sc/flux?DATE={date}&FREQUENCY={spix_q}&NAME={Fcal_name}"
    req = request.Request(url=url, method="GET")
    r = request.urlopen(req).read()

    votable = parse_votable(io.BytesIO(r))

    spix_F = votable["FluxDensity"][0]
    slope = votable["SpectralIndex"][0]

    return spix_q, spix_F, slope
