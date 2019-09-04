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

import os
import logging
import time
import urllib2

import boto3
from botocore import session
from botocore.exceptions import ClientError
import requests
from s3transfer.manager import TransferManager

class ConfigurationException(Exception):
    pass

def _get_client(s3region=None):
    """Configure a client object for uploading to AWS S3.

:type s3region: string
:param s3region: name of the AWS region to target, e.g. 'us-east-1'

The 's3region' parameter can be used to override whatever default region
boto would normally pick. If not passed explicitly, we will also look
for a value in the 'AWS_REGION' environment variable. Credentials are as
determined by boto normally; in the case of a Lambda invocation, boto
will look for credentials in 'AWS_ACCESS_KEY_ID' and
'AWS_SECRET_ACCESS_KEY' variables. See:

https://boto3.readthedocs.io/en/latest/guide/configuration.html#environment-variables

for more details."""
    
    if s3region is not None:
        return session.get_session().create_client('s3', s3region)
    if 'AWS_REGION' in os.environ:
        return session.get_session().create_client('s3', os.environ['AWS_REGION'])
    return session.get_session().create_client('s3')

def _field_equal(src, hdr, obj, key):
    """Checks whether source has the same field value as the given S3 object.

:param src: file-like object as returned by urllib2.urlopen

:type hdr: string
:param hdr: name of the HTTP header to check on the source

:type obj: dict
:param obj: S3 object

:type key: string
:param key: S3 object attribute name"""
    h = src.info().getheader(hdr)
    if h is None:
        return (key not in obj or obj[key] is None)
    if key not in obj: return False
    return (h == obj[key])

def _meta_equal(src, hdr, obj, key):
    """Checks whether source has the same header value as recorded in S3 object metadata.

:param src: file-like object as returned by urllib2.urlopen

:type hdr: string
:param hdr: name of the HTTP header to check on the source

:type obj: dict
:param obj: S3 object

:type key: string
:param key: name of the S3 object metadata key"""
    k = key.lower()
    h = src.info().getheader(hdr)
    if h is None:
        return ('Metadata' not in obj or k not in obj['Metadata'] or
                obj['Metadata'][k] is None)
    if 'Metadata' not in obj or k not in obj['Metadata']: return False
    return (h == obj['Metadata'][k])

def _is_up_to_date(src, s3client, s3bucket, s3key):
    """Checks whether an S3 object is up-to-date with the source.

:param src: file-like object as returned by urllib2.urlopen

:type client: botocore.client.S3
:param client: S3 client

:type s3bucket: string
:param s3bucket: S3 bucket name

:type s3key: string
:param s3key: S3 object key name

Compares the source's HTTP response headers with the destination
S3 object's metadata to see if we can skip a download (because
we've already gotten it). Errs on the side of re-downloading."""
    try:
        obj = s3client.get_object(Bucket=s3bucket, Key=s3key)
    except ClientError:
        return False

    return (_field_equal(src, 'Content-Encoding', obj, 'ContentEncoding') and
            _field_equal(src, 'Content-Type', obj, 'ContentType') and
            _meta_equal(src, 'ETag', obj, 'src-etag') and
            _meta_equal(src, 'Last-Modified', obj, 'src-last-modified'))

def _set_upload_arg(args, src, src_hdr, upload_arg):
    if src.info().getheader(src_hdr) is not None:
        args[upload_arg] = src.info().getheader(src_hdr)

def _set_metadata(args, src):
    if src.info().getheader('ETag') is not None:
        if 'Metadata' not in args: args['Metadata'] = {}
        args['Metadata']['src-etag'] = src.info().getheader('ETag')
    if src.info().getheader('Last-Modified') is not None:
        if 'Metadata' not in args: args['Metadata'] = {}
        args['Metadata']['src-last-modified'] = src.info().getheader('Last-Modified')
        
def download_url(url, s3key, s3client=None, s3bucket=None, s3region=None):
    """Downloads the given URL to the given S3 destination object.

:type url: string
:param url: source URL to download

:type s3key: string
:param s3key: key name for the destination S3 object

:type s3client: botocore.client.S3
:param s3client: S3 client to use (optional)

:type s3bucket: string
:param s3bucket: destination S3 bucket name (optional)

:type s3region: string
:param s3region: destination AWS region, e.g. 'us-east-1' (optional)

Will download the content at the given URL to the given S3 destination. Will
consult the usual boto environment variables and configuration to create a
client as needed. If the destination region is not provided, the AWS_REGION
environment variable will be consulted instead."""
    if s3client is not None:
        s3c = s3client
    else:
        s3c = _get_client(s3region)

    if s3bucket is None and 'AWS_S3_BUCKET' not in os.environ:
        msg = "No S3 bucket name configured"
        logging.error(msg)
        raise ConfigurationException(msg)
    if s3bucket is None: s3bucket = os.environ['AWS_S3_BUCKET']

    try:
        logging.info("Validating existence of bucket %s..." % s3bucket)
        start = time.time()
        s3c.head_bucket(Bucket=s3bucket)
        end = time.time()
        logging.info("Bucket %s exists (%ld ms)" %
                            (s3bucket, long((end - start) * 1000.0)))
    except ClientError as e:
        logging.info("Creating bucket %s..." % s3bucket)
        start = time.time()
        s3c.create_bucket(Bucket=s3bucket)
        end = time.time()
        logging.info("Created bucket %s (%ld ms)" %
                            (s3bucket, long((end - start) * 1000.0)))
    
    logging.info("Checking metadata on %s..." % url)
    start = time.time()
    req = urllib2.Request(url, headers={'Accept-Encoding': 'gzip'})
    u = urllib2.urlopen(req)
    end = time.time()
    logging.info("Fetched metadata on %s (%ld ms)" %
                        (url, long((end - start) * 1000.0)))

    if _is_up_to_date(u, s3c, s3bucket, s3key):
        u.close()
        logging.info("Skipping download of %s to s3://%s/%s (up-to-date)" %
                            (url, s3bucket, s3key))
        return
    
    tm = TransferManager(s3c)
    extra_args = { 'ACL' : 'private' }
    _set_upload_arg(extra_args, u, 'Content-Encoding', 'ContentEncoding')
    _set_upload_arg(extra_args, u, 'Content-Type', 'ContentType')
    _set_metadata(extra_args, u)

    logging.info("Beginning download of %s to s3://%s/%s..." %
                        (url, s3bucket, s3key))
    start = time.time()
    f = tm.upload(u, s3bucket, s3key, extra_args=extra_args)
    f.result()
    end = time.time()
    logging.info("Download of %s to s3://%s/%s complete (%ld ms)" %
                        (url, s3bucket, s3key,
                         long((end - start) * 1000.0)))
