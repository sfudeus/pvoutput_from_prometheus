# PVOutput.org from Prometheus importer

This simple project takes data by querying a defined prometheus instance and submits that data to [pvoutput.org](https://pvoutput.org). The prometheus queries are defined in code according to my needs but they can easily be adapted to your requirements.
There was no need yet to make them configurable, but this culd be easily added.

## Usage:
```sh
usage: pvoutput_reporter.py [-h] --mode {daily,live} --api-key API_KEY --system-id SYSTEM_ID --prometheus-url
                            PROMETHEUS_URL [--pvoutput-url PVOUTPUT_URL] [--ca-path CA_PATH]
                            [--iso-timestamp ISO_TIMESTAMP] [--timezone TIMEZONE] [--debug] [--dry-run]
```

Using `--dry-run` will query your prometheus and then show what it would be submitting to pvoutput in normal mode.

## Report daily data

When executing it with `--mode daily` and without `--iso-timestamp`, data for "yesterday" is imported into pvoutput. The script is supposed to be invoked on a daily basis.

## Report live data

When executing with `--mode live`, the pvoutput status API is used and live data is submitted.

## Importing old data

By using `--iso-timestamp`, you can define the day for which you want to import historic data (given that this data does exist in your prometheus instance).

## Custom CA

If your prometheus instance is using a HTTPS certificate from a custom CA, you can refer to that ca-cert file by using ``--ca-path`.

## Container image

A container image will automatically by built from weekly from main (and tagged latest) and once from each feature branch.
They can be found at sfudeus/pvoutput_from_prometheus on Docker hub.
