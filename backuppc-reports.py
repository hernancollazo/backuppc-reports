#!/usr/bin/env python
# -*- coding: utf-8 -*-
# encoding=utf8
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4

#
# backuppc-reports -- A simple script to interact with the BackupPc
# summary interface from command line.
#
# Copyright 2021 - Hernán Collazo <hernan.collazo@gmail.com>
#
# Please send mail to me if you find bugs or have any suggestions.
#

import urllib3
import argparse
import requests
import sys
import warnings
import smtplib
import os.path
from email.mime.text import MIMEText
from requests.auth import HTTPBasicAuth
from configparser import ConfigParser
from termcolor import colored
from bs4 import BeautifulSoup
from beautifultable import BeautifulTable

urllib3.disable_warnings()
warnings.simplefilter(action='ignore', category=FutureWarning)

VERSION = "1.0b"


def banner():
    """ Banner """
    print(r"""
   ___            _
  / __\ __ _  ___| | ___   _ _ __  _ __   ___
 /__\/// _` |/ __| |/ / | | | '_ \| '_ \ / __|
/ \/  \ (_| | (__|   <| |_| | |_) | |_) | (__
\_____/\__,_|\___|_|\_\\__,_| .__/| .__/ \___|
                            |_|   |_|
REPORTS
By Hernán Collazo - hernan.collazo@gmail.com
Freely distributed under the MIT license.
    """)
    return


def get_backup_data():
    """ Get all data from BackupPc GUI and return this as a dictionary """
    try:
        page = requests.get(
            backuppc_url,
            auth=HTTPBasicAuth(backuppc_username, backuppc_password),
            verify=False, timeout=30)
    except requests.exceptions.Timeout:
        sendEmail(
            'BackupPc Monitor - Timeout connecting to BackupPc',
            'Got a timeout error trying to connect to BackupPc.')
        print("ERROR: The request to BackupPc timed out.")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        sendEmail(
            'BackupPc Monitor - Error connecting to BackupPc',
            'Got a error trying to connect to BackupPc')
        print("ERROR: ", e)
        sys.exit(1)
    soup = BeautifulSoup(page.text, "lxml")
    soup
    table = soup.find('table', id='host_summary_backups')
    backuppc_data = []
    for row in table.find_all('tr')[1:]:
        data = row.find_all('td')
        row_data = [td.text.strip() for td in data]
        # ['Host', 'User', '#Full', 'Full Age (days)', 'Full Size (GB)',
        # 'Speed (MB/s)', '#Incr', 'Incr Age (days)',
        # 'Last Backup (days)', 'State', '#Xfer errs', 'Last attempt']
        backuppc_host = {
            'hostname': row_data[0],
            'user': row_data[1],
            'num_full_bkps': row_data[2],
            'full_bkp_age': row_data[3],
            'full_size_gb': row_data[4],
            'speed': row_data[5],
            'num_incr_bkps': row_data[6],
            'incr_bkp_age': row_data[7],
            'last_bkp_days': row_data[8],
            'state': row_data[9],
            'xfer_errors': row_data[10],
            'last_attempt': row_data[11],
        }
        backuppc_data.append(backuppc_host)
    return backuppc_data


def get_host(hostname):
    """ Get information about backups for a particular host """
    print(f"\nSearching for host '{hostname}'...\n")
    backuppc_data = get_backup_data()
    for host in backuppc_data:
        if host['hostname'] == hostname:
            return host


def sendEmail(subject, body):
    """ Send email notifications using smtplib """
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = email_from
    msg['To'] = email_to
    s = smtplib.SMTP(smtp_server, smtp_port)
    s.set_debuglevel(0)
    s.ehlo()
    if smtp_tls == 1:
        print("Using TLS")
        s.starttls()
    s.ehlo()
    if smtp_user != 'NULL' and smtp_pass != 'NULL':
        print("Using USER/PASS for SMTP")
        s.login(smtp_user, smtp_pass)
    try:
        s.sendmail(email_from, email_to, msg.as_string())
    except Exception as e:
        print('Error trying to send mail. Please check your SMTP settings.')
        print(f'{e}')
    s.quit()
    return


# Main
if (__name__ == "__main__"):
    banner()
    # Get OS arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c", "--config",
        default='/opt/backuppc-reports/backuppc-reports.cfg',
        help="Config file full path.")
    subparser = parser.add_subparsers(dest='command')
    summary = subparser.add_parser(
        'summary', help='Show a summary of all hosts in BackupPc.')
    monitor = subparser.add_parser(
        'monitor',
        help='Check that there are no failed backups and if there are, '
             'send an alert by email.')
    version = subparser.add_parser(
        'version', help='Display the current version and exit.')
    checkhost = subparser.add_parser(
        'hostinfo', help='Show a report about backups for a particular host.')
    checkhost.add_argument('--server', type=str, required=True)
    args = parser.parse_args()
    # Read values from config file
    config_file = args.config
    print(f'Using config file: {config_file}\n')
    if not os.path.isfile(config_file):
        print('FATAL ERROR: Config file not found. Aborting.')
        sys.exit(1)
    config_parser = ConfigParser()
    config_parser.read(config_file)
    try:
        backuppc_url = config_parser.get('backuppc', 'url')
        backuppc_username = config_parser.get('backuppc', 'username')
        backuppc_password = config_parser.get('backuppc', 'password')
        max_full_backup_age = int(
            config_parser.get('general', 'max_full_backup_age'))
        max_incr_backup_age = int(
            config_parser.get('general', 'max_incr_backup_age'))
        last_backup_age = int(
            config_parser.get('general', 'last_backup_age'))
        email_to = config_parser.get('notifications', 'email_to')
        email_from = config_parser.get('notifications', 'email_from')
        smtp_server = config_parser.get('notifications', 'smtp_server')
        smtp_port = config_parser.get('notifications', 'smtp_port')
        smtp_user = config_parser.get('notifications', 'smtp_user')
        smtp_pass = config_parser.get('notifications', 'smtp_pass')
        smtp_tls = config_parser.get('notifications', 'smtp_tls')
    except Exception:
        print("FATAL ERROR: There are errors in the configuration file. "
              "Please, verify that everything is ok there.")
        print('You can use the backuppc-reports.cfg.dist file as example.')
        sys.exit(1)
    if args.command == 'summary':
        backuppc_data = get_backup_data()
        table = BeautifulTable(maxwidth=120)
        table.column_widths = [20, 15, 10, 10, 10, 20]
        table.columns.header = [
            "Hostname",
            "Last Full Backup Age",
            "Last Incr. Backup Age",
            "Last Backup",
            "Last attempt",
            "State"
        ]
        for host_data in backuppc_data:
            table.rows.append([
                host_data["hostname"],
                host_data["full_bkp_age"],
                host_data["incr_bkp_age"],
                host_data["last_bkp_days"],
                host_data["last_attempt"],
                host_data["state"],
            ])
        # table.set_style(BeautifulTable.STYLE_COMPACT)
        print(table)
        print("\n")
    elif args.command == 'hostinfo':
        host_data = get_host(args.server)
        if host_data is None:
            print("ERROR: Host NOT FOUND in Backuppc.")
            sys.exit(1)
        else:
            table = BeautifulTable()
            table.rows.append(["Hostname", host_data["hostname"]])
            table.rows.append(["Username", host_data["user"]])
            table.rows.append(["# Full Backups", host_data["num_full_bkps"]])
            if float(host_data["full_bkp_age"]) > float(max_full_backup_age):
                table.rows.append([
                    "Last Full Backups Age",
                    colored(host_data["full_bkp_age"], 'red')])
            else:
                table.rows.append([
                    "Last Full Backups Age", host_data["full_bkp_age"]])
            table.rows.append([
                "Full Backup Size (Gb)", host_data["full_size_gb"]])
            table.rows.append([
                "# Incremental Backups", host_data["num_incr_bkps"]])
            if float(host_data["incr_bkp_age"]) > float(max_incr_backup_age):
                table.rows.append([
                    "Last Incremental Backup Age",
                    colored(host_data["incr_bkp_age"], 'red')])
            else:
                table.rows.append([
                    "Last Incremental Backup Age", host_data["incr_bkp_age"]])
            table.rows.append([
                "Last Backup (Days Ago)", host_data["last_bkp_days"]])
            table.rows.append(["Host State", host_data["state"]])
            table.rows.append([
                "XFER Errors in Last Backup", host_data["xfer_errors"]])
            table.rows.append(["Last attempt", host_data["last_attempt"]])
            print(table)
            print("\n")
    elif args.command == 'monitor':
        backuppc_data = get_backup_data()
        host_count = 0
        ignored_host = 0
        host_with_errors = 0
        for host_data in backuppc_data:
            host_count += 1
            errors = 0
            error_msg = ""
            if host_data["state"] == 'auto disabled':
                ignored_host += 1
                print('Ignoring host %s - disabled by user.'
                      % (host_data["hostname"]))
            else:
                full_age = float(host_data["full_bkp_age"])
                if full_age > float(max_full_backup_age):
                    errors += 1
                    error_msg = (
                        error_msg +
                        "\nERROR: The last full backup of server '%s' is "
                        "older (%s days) than expected (%s days)."
                        % (host_data["hostname"], host_data["full_bkp_age"],
                           max_full_backup_age))
                incr_age = float(host_data["incr_bkp_age"])
                if incr_age > float(max_incr_backup_age):
                    errors += 1
                    error_msg = (
                        error_msg +
                        "\nERROR: The last incremental backup of server '%s' "
                        "is older (%s days) than expected (%s days)."
                        % (host_data["hostname"], host_data["incr_bkp_age"],
                           max_incr_backup_age))
                if float(host_data["last_bkp_days"]) > float(last_backup_age):
                    errors += 1
                    error_msg = (
                        error_msg +
                        "\nERROR: The last backup of server '%s' is older "
                        "(%s days) than expected (%s days)."
                        % (host_data["hostname"], host_data["last_bkp_days"],
                           last_backup_age))
                if errors > 0:
                    sendEmail(
                        'BackupPc Monitor - Problems found with server %s'
                        % (host_data["hostname"]), error_msg)
                    print(error_msg)
                    host_with_errors += 1
        print(f"\nTotal Hosts: {host_count}")
        print(f"Ignored Hosts: {ignored_host}")
        print(f"Hosts with problems: {host_with_errors}")
    elif args.command == 'version':
        print(f"version {VERSION}\n")
    else:
        print('Error: Invalid command. Please use --help to see the '
              'available commands.')
