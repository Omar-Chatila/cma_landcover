# Environmental Land Cover Annotation

MoveApps App for adding environmental land-cover information to animal tracks.

GitHub repository: [Omar-Chatila/cma_landcover](https://github.com/Omar-Chatila/cma_landcover)

## Description

This App annotates every location in a
`movingpandas.TrajectoryCollection` with a terrain code and a readable terrain
name. Processing is independent for each animal, so each track gets its own
environment raster, grid, and projected coordinate reference system (CRS).

The App supports any taxon with point locations and a defined input CRS. It
offers two deliberately different data modes:

- **LONG_RANGE** is the safe default for bird, marine, migratory, or otherwise
  wide-ranging studies, especially when tracks may cross UTM zones. It uses
  packaged [Natural Earth 1:10m land polygons](https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-land/)
  and annotates only `Land` or `Water`. It does not contact a land-cover API.
- **LOCAL** provides detailed land-cover classes from ESA WorldCover. Select it
  only when the study is known to be spatially local. It requires network access
  to the Microsoft Planetary Computer during the App run.

If the extent is uncertain, use **LONG_RANGE**.

## Input and output

The input and returned output are both a
`movingpandas.TrajectoryCollection`. Each input trajectory must contain valid
point geometries, timestamps, animal identifiers, and a defined CRS. The App
preserves the input trajectories and columns and adds:

- `terrain`: numeric terrain code;
- `terrain_name`: readable class name;
- `grid_x` and `grid_y`: the location's cell in the per-animal discrete grid;
- `utm_x`, `utm_y`, and `utm_crs` when **Add UTM conversion** is enabled.

The UTM columns are useful only together: `utm_crs` identifies the CRS in which
the row's `utm_x` and `utm_y` values are expressed.

## Settings

### Study range type (`range_type`)

**LONG_RANGE** creates a binary land/water raster from the Natural Earth 1:10m
land polygons bundled with `environmentcma`:

| Code | Class |
| ---: | --- |
| 10 | Land |
| 80 | Water |

**LOCAL** obtains ESA WorldCover through the
[Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/dataset/esa-worldcover).
WorldCover is a global 10 m product derived from Sentinel-1 and Sentinel-2 data.
The App searches the public Planetary Computer STAC endpoint for collection
`esa-worldcover` using each animal's bounding box, opens the matching item's
`map` asset, and clips it to that area of interest.

The detailed classes are:

| Code | ESA WorldCover class |
| ---: | --- |
| 10 | Tree cover |
| 20 | Shrubland |
| 30 | Grassland |
| 40 | Cropland |
| 50 | Built-up |
| 60 | Bare / sparse vegetation |
| 70 | Snow and ice |
| 80 | Permanent water bodies |
| 90 | Herbaceous wetland |
| 95 | Mangroves |
| 100 | Moss and lichen |

ESA describes WorldCover 2020 and 2021 as freely accessible global 10 m maps
with 11 classes; see the [ESA WorldCover project description](https://esa-worldcover.org/en/about/about).
The Planetary Computer provides discovery metadata through its public STAC API
and signed access to the raster asset stored on Azure. The downloaded imagery
remains an ESA WorldCover product; Planetary Computer is the access platform.

### Add UTM conversion (`addUtm`)

When enabled, the App adds `utm_x`, `utm_y`, and `utm_crs`. For each animal it
selects the WGS 84 UTM zone containing the spatial centre of that animal's
track. All fixes belonging to that animal use the same UTM CRS, independently
of every other animal.

The intermediate GeoTIFF must be projected before the discrete metric grid is
created and before locations are sampled. Both modes first create or clip a
raster in geographic WGS 84 coordinates (EPSG:4326), then reproject it in place
to the local WGS 84 UTM CRS. Northern-hemisphere zones use EPSG:326xx and
southern-hemisphere zones use EPSG:327xx, where `xx` is the UTM zone. This makes
the per-animal grid calculations operate in metres rather than degrees.

### Keep GeoTIFF files (`keepGeoTiffs`)

When enabled, all per-animal GeoTIFFs are returned as one downloadable MoveApps
artifact named `tiffs.zip`. The paths inside the archive identify their
`landcover` subdirectory and animal-specific filenames. In **LOCAL** mode these
are clipped ESA WorldCover rasters; in **LONG_RANGE** mode they are rasters
generated from the packaged Natural Earth polygons. When disabled, rasters and
discrete text grids are temporary processing files and are deleted after the
App run.

## Processing details

For each animal the App:

1. transforms its extent to EPSG:4326 and adds a small spatial buffer;
2. obtains detailed WorldCover data for **LOCAL**, or rasterizes packaged land
   polygons for **LONG_RANGE**;
3. reprojects the GeoTIFF to the UTM zone selected from the raster centre;
4. creates a regular discrete grid with a maximum dimension of 1,000 cells;
5. samples the projected raster at every fix and adds the annotation columns.

Natural Earth is a small-scale cartographic data set, so **LONG_RANGE** is
appropriate for broad land/water context rather than fine coastline or small
island analysis. ESA WorldCover is more detailed, but its class accuracy and
reference year should be considered when interpreting results.

## Most common errors

- **Missing CRS:** the App cannot transform or sample locations without a
  defined input CRS. Assign the correct CRS before running it.
- **LOCAL data cannot be fetched:** Planetary Computer access may be unavailable
  or no WorldCover item may cover the supplied bounding box. Retry later, check
  the coordinates, or use **LONG_RANGE** if detailed local classes are not
  required.
- **Unexpected results for a wide-ranging track:** run the study with
  **LONG_RANGE**. Use **LOCAL** only for a study known to be local.
- **No `tiffs.zip`:** enable **Keep GeoTIFF files**. The intermediate files are
  intentionally deleted when this setting is disabled.

Invalid settings, empty collections, invalid geometries, and annotation or
raster-processing failures stop the App with an error instead of silently
returning partially annotated tracks.
