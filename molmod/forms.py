#!/usr/bin/env python3
"""
This module defines classes used for creating form objects in route modules.
It also includes (server-side) validation of form input.
"""

import re

from flask import current_app as APP
from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import (BooleanField, IntegerField, SelectMultipleField,
                     SubmitField, TextAreaField, ValidationError)

DEFAULT_BLAST_GENE = """>test-seq-1
TGGGGAATTTTGCGCAATGGGGGAAACCCTGACGCAGCAACGCCGCGTGGAGGATGAAGTCCCTTGGGACGTAAACTCCTTTCGACCGGGACGATTATGACGGTACCGGTGGAAGAAGCCCCGGCTAACTTCGTGCCAGCAGCCGCGGTAATACGAGGGGGGCAAGCGTTGTTCGGAATTATTGGGCGTAAAGGGCGCGTAGGCGGTGCGGTAAGTCACCTGTGAAACCTCTGGGCTCAACCCAGAGCCTGCAGGCGAAACTGCCGTGCTGGAGTATGGGAGAGGTGCGTGGAATTCCCGGTGTAGCGGTGAAATGCGTAGATATCGGGAGGAACACCTGTGGCGAAAGCGGCGCACTGGACCATAACTGACGCTGAGGCGCGAAAGCTAGGGGAGCAAACA
>test-seq-2
TGGGGAATTTTGCGCAATGGGGGAAACCCTGACGCAGCAACGCCGCGTGGAGGATGAAGCCCCTTGGGGTGTAAACTCCTTTCGATCGGGACGATTATGACGGTACCGGATGAAGAAGCACCGGCTAACTCTGTGCCAGCAGCCGCGGTAATACAGAGGGTGCAAGCGTTGTTCGGAATTATTGGGCGTAAAGGGTGCGTAGGCGGTGCGGTAAGTCTTTTGTGAAATCTCCGGGCTCAACCCGGAGCCTGCAAGGGAAACTGCCGTGCTTGAGTGTGGGAGAGGTGAGTGGAATTCCCGGTGTAGCGGTGAAATGCGTAGATATCGGGAGGAACACCTGTGGCGAAAGCGGCTCACTGGACCACAACTGACGCTGATGCACGAAAGCTAGGGGAGCAAACA
"""


def fasta_check(form, field):
    if len(field.data) < 1:
        raise ValidationError('Please submit an input sequence')
    if len(field.data) > 50000:
        raise ValidationError("""Input sequence must be less
                              than 50000 characters""")

    # Check that this is actually a valid fasta file, that we can process
    fasta_chars = r'AaCcGgTtUuIiRrYyKkMmSsWwBbDdHhVvNn\-'
    title_pattern = r'^>[\w.,\-]+$'
    seq_pattern = f'^[{fasta_chars}]+$'

    # I tried to use re.fullmatch here, but it became _very_ slow, so I wrote
    # this very simple parser instead. This has the added bonus that it gives
    # user friendly validation messages.
    hasSeq = True
    isHeader = True
    currentHeader = ''
    # Add an empty last row to catch empty headers easily
    for row in re.split('[\r\n]+', field.data):
        row = row.strip()
        # Allow empty lines
        if len(row) == 0:
            continue
        # If we have a second header without first getting a sequence for the
        # last header
        if row.startswith('>'):
            if not hasSeq:
                raise ValidationError('All Fasta headers require a sequence')
            isHeader = True
            hasSeq = False
            currentHeader = row

        if isHeader:
            if not re.match(title_pattern, row):
                raise ValidationError('Malformed header: %s' % row)
            isHeader = False
        else:
            if re.match(seq_pattern, row):
                hasSeq = True
            else:
                raise ValidationError('Unknown characters in %s: %s' % (
                                      currentHeader,
                                      re.sub(f'[{fasta_chars}]+', '', row)
                                      ))
    if not hasSeq:
        raise ValidationError('All Fasta headers require a sequence')


def identity_check(form, field):
    # Check max value, min value
    if field.data is not None:
        try:
            data_i = int(field.data)
        except Exception:
            return None
        if data_i < 0 or data_i > 100:
            raise ValidationError('Value between 0 and 100, please.')


def cover_check(form, field):
    # Check max value, min value
    if field.data is not None:
        try:
            data_i = int(field.data)
        except Exception:
            return None
        if data_i < 0 or data_i > 100:
            raise ValidationError('Value between 0 and 100, please.')


def file_check(form, field):
    """Checks that data delivery uploads have correct format. See also main.js
    for file size validation that is performed in browser, for quicker
    response, and limits to file upload size set both in .env and in proxy
    config:
    https://github.com/biodiversitydata-se/proxy-ws-mol-mod-docker/blob/master/nginx-proxy.conf
    """
    file = field.data
    valid_ext = APP.config['VALID_EXTENSIONS']
    ext_str = ", ".join(valid_ext)

    if not file or not file.filename:
        raise ValidationError('Please select a file.')

    # Same validation (with differently worded msg) is run by jQuery
    # to respond (i.e. reject) faster for large files, but I keep this for now
    parts = file.filename.lower().split('.')
    APP.logger.debug(f'{file.filename} is split into {parts}')

    if len(parts) < 2:
        raise ValidationError(f'Please select a valid file ({ext_str}).')

    if (parts[-1] in valid_ext) or (parts[-2] + '.' + parts[-1] in valid_ext):
        APP.logger.debug(f'Approving file name {file.filename}')
        return None

    raise ValidationError(f'Please select a valid file ({ext_str}).')


class BlastSearchForm(FlaskForm):
    sequence = TextAreaField(u'sequence', [fasta_check],
                             default=DEFAULT_BLAST_GENE)
    min_identity = IntegerField(u'min_identity', [identity_check], default=100)
    min_qry_cover = IntegerField(u'min_qry_cover', [cover_check], default=100)
    blast_for_seq = SubmitField(u'BLAST')


class BlastResultForm(FlaskForm):
    asv_id = BooleanField(u'asv_id')
    batch_url = APP.config['BATCH_SEARCH_URL']
    redirect_url = APP.config['REDIRECT_URL']


class FilterSearchForm(FlaskForm):
    gene = SelectMultipleField('gene', choices=[])
    sub = SelectMultipleField('sub', choices=[])
    fw_prim = SelectMultipleField('fw_prim', choices=[])
    rv_prim = SelectMultipleField('rv_prim', choices=[])
    kingdom = SelectMultipleField('kingdom', choices=[])
    phylum = SelectMultipleField('phylum', choices=[])
    classs = SelectMultipleField('classs', choices=[])
    oorder = SelectMultipleField('oorder', choices=[])
    family = SelectMultipleField('family', choices=[])
    genus = SelectMultipleField('genus', choices=[])
    species = SelectMultipleField('species', choices=[])
    filter_asvs = SubmitField(u'Filter')


class FilterResultForm(FlaskForm):
    asv_id = BooleanField(u'asv_id')
    batch_url = APP.config['BATCH_SEARCH_URL']
    redirect_url = APP.config['REDIRECT_URL']


class UploadForm(FlaskForm):
    file = FileField('file', [file_check])
    submit = SubmitField('Submit')


class DownloadForm(FlaskForm):
    ipt_resource_id = BooleanField(u'ipt_resource_id')
    download = SubmitField(u'Download')
