#!/usr/bin/env python3
import argparse
import logging
import json
from datetime import date, time, datetime, timedelta
from zoneinfo import ZoneInfo
import requests


def midnight(my_dt: datetime):
    return my_dt.replace(hour=0, minute=0, second=0)


class PvoutputReporter():

    prometheus_url: str = ''
    pvoutput_url: str = ''
    pvoutput_api_key: str = ''
    pvoutput_system_id: str = ''
    dry_run: bool = False
    ca_path: str = None
    processing_date: datetime = None
    reporting_date: date = None
    timezone: ZoneInfo = None

    def __init__(self, prometheus_url: str, pvoutput_url: str, pvoutput_api_key: str,
                 pvoutput_system_id: str, dry_run: bool, ca_path: str, timezone: ZoneInfo):
        self.prometheus_url = prometheus_url
        self.pvoutput_url = pvoutput_url
        self.pvoutput_api_key = pvoutput_api_key
        self.pvoutput_system_id = pvoutput_system_id
        self.dry_run = dry_run
        self.ca_path = ca_path
        self.timezone = timezone

    def set_processing_date(self, processing_date: datetime):
        logging.debug("Set processing date to %s", processing_date.isoformat())
        self.processing_date = processing_date
        self.reporting_date = (processing_date-timedelta(days=1)).date()

    def set_reporting_date(self, reporting_date: date):
        logging.debug("Set reporting date to %s", reporting_date.isoformat())
        processing_date = datetime.fromisoformat(reporting_date.isoformat())
        processing_date = datetime.combine(
            reporting_date+timedelta(days=1), time(), tzinfo=self.timezone)

        self.set_processing_date(processing_date)

    def query_prometheus(self, query):
        logging.debug("Prom-Query: %s", query)
        response = requests.get(self.prometheus_url + '/api/v1/query', params={
            'query': query, 'time': self.processing_date.timestamp()}, verify=self.ca_path)
        response.raise_for_status()

        response_json = response.json()

        if len(response_json['data']['result']) == 0:
            raise Exception("No data received from prometheus")

        value = float(response.json()['data']['result'][0]['value'][1])
        logging.debug("Retrieved %f", value)
        return value

    def submit(self, data: dict, path: str):
        if self.dry_run:
            logging.info("Would send %s", json.dumps(data))
            return

        headers = {"X-Pvoutput-Apikey": self.pvoutput_api_key,
                   "X-Pvoutput-SystemId": self.pvoutput_system_id}
        submit_response = requests.post(
            self.pvoutput_url + path, data=data, headers=headers)
        logging.debug(submit_response.text)
        submit_response.raise_for_status()

        logging.info("Successfully submitted data for %s", data["d"])

    def daily(self):

        self.set_processing_date(midnight(datetime.now(tz=self.timezone)))

        data = {}
        data["d"] = self.reporting_date.strftime("%Y%m%d")
        data["g"] = int(self.query_prometheus(
            'sum(delta(rctmon_energy_solar_generator_sum[1d]))'))
        data["e"] = int(self.query_prometheus(
            'abs(sum(delta(rctmon_energy_grid_feed_sum[1d])))'))
        data["pp"] = int(self.query_prometheus(
            'max_over_time(sum(rctmon_generator_power_watt)[1d])'))
        data["c"] = int(self.query_prometheus(
            'sum(delta(rctmon_energy_household_sum[1d]))'))
        data["tm"] = self.query_prometheus(
            'min_over_time(homematic_actual_temperature{device_type="WEATHER_TRANSMIT"}[1d])')
        data["tx"] = self.query_prometheus(
            'max_over_time(homematic_actual_temperature{device_type="WEATHER_TRANSMIT"}[1d])')

        self.submit(data, "/service/r2/addoutput.jsp")

    def live(self):

        self.set_processing_date(datetime.now(tz=self.timezone))

        data = {}
        data["d"] = self.processing_date.strftime("%Y%m%d")
        data["t"] = self.processing_date.strftime("%H:%M")
        data["v1"] = int(self.query_prometheus(
            'sum(rctmon_energy_solar_generator_sum)'))
        data["v2"] = int(self.query_prometheus(
            'sum(rctmon_generator_power_watt)'))
        data["v3"] = int(self.query_prometheus(
            'sum(rctmon_energy_household_sum)'))
        data["v4"] = int(self.query_prometheus(
            'abs(sum(rctmon_household_load))'))
        data["v5"] = self.query_prometheus(
            'homematic_actual_temperature{device_type="WEATHER_TRANSMIT"}')
        data["v6"] = self.query_prometheus('avg(rctmon_grid_voltage_volt)')
        data["c1"] = 1
        data["n"] = 0

        self.submit(data, "/service/r2/addstatus.jsp")


if __name__ == '__main__':

    PARSER = argparse.ArgumentParser()
    PARSER.add_argument("--mode", required=True, choices=['daily', 'live'],
                        help="Report daily output data or live status data")
    PARSER.add_argument("--api-key", required=True,
                        help="API key for pvoutput.org")
    PARSER.add_argument("--system-id", required=True,
                        help="System id for pvoutput.org")
    PARSER.add_argument("--prometheus-url", required=True,
                        help="Base-URL to your prometheus instance")
    PARSER.add_argument("--pvoutput-url", default="https://pvoutput.org")
    PARSER.add_argument(
        "--ca-path", help="Path to a custom CA certificate for prometheus requests")
    PARSER.add_argument("--iso-timestamp",
                        help="An iso-timestamp used for postprocessing data")
    PARSER.add_argument("--timezone", default="Europe/Berlin",
                        help="Your timezone - default to Europe/Berlin")
    PARSER.add_argument("--debug", action="store_true")
    PARSER.add_argument("--dry-run", action="store_true")
    ARGS = PARSER.parse_args()

    if ARGS.debug:
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s - %(levelname)s - %(message)s')
    else:
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')

    PROCESSOR = PvoutputReporter(
        ARGS.prometheus_url, ARGS.pvoutput_url, ARGS.api_key, ARGS.system_id, ARGS.dry_run,
        ARGS.ca_path, ZoneInfo(ARGS.timezone))

    if ARGS.iso_timestamp:
        PROCESSOR.set_reporting_date(
            date.fromisoformat(ARGS.iso_timestamp))

    if ARGS.mode == 'daily':
        PROCESSOR.daily()
    elif ARGS.mode == 'live':
        PROCESSOR.live()
