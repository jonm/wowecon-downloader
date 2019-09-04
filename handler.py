# Copyright (C) 2018 Jonathan Moore
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import os

import battlenet
import downloader

logging.getLogger().setLevel(logging.INFO)

def _get_configuration():
    config = {}
    config['wow_api_endpoint'] = os.getenv('WOW_API_ENDPOINT',
                                           'https://us.api.blizzard.com')
    config['wow_client_id'] = os.environ['WOW_CLIENT_ID']
    config['wow_client_secret'] = os.environ['WOW_CLIENT_SECRET']
    config['wow_realm'] = os.getenv('WOW_REALM','thrall')
    config['wow_locale'] = os.getenv('WOW_LOCALE','en_US')
    config['aws_region'] = os.getenv('AWS_REGION','us-east-1')
    config['s3_bucket_name'] = os.environ['S3_BUCKET']
    return config

def _keyname_from_datetime(config, dt):
    return "%s/%s" % (config['wow_realm'], dt.isoformat())

def download_handler(event, context):
    config = _get_configuration()
    wowc = battlenet.WoWCommunityAPIClient(config['wow_client_id'],
                                           config['wow_client_secret'],
                                           endpoint=config['wow_api_endpoint'])
    for batch in wowc.get_auction_data_status(config['wow_realm'],
                                              config['wow_locale']):
        s3key = _keyname_from_datetime(config, batch.last_modified)
        downloader.download_url(batch.url,
                                s3key,
                                s3bucket=config['s3_bucket_name'],
                                s3region=config['aws_region'])
    return
                                
