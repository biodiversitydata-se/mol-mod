from flask import current_app as app
from flask_wtf import FlaskForm
from wtforms import (BooleanField, IntegerField, SelectMultipleField,
                     StringField, SubmitField, TextAreaField, ValidationError)

DEFAULT_BLAST_GENE = """>test-seq-1
TGGGGAATTTTGCGCAATGGGGGAAACCCTGACGCAGCAACGCCGCGTGGAGGATGAAGTCCCTTGGGACGTAAACTCCTTTCGACCGGGACGATTATGACGGTACCGGTGGAAGAAGCCCCGGCTAACTTCGTGCCAGCAGCCGCGGTAATACGAGGGGGGCAAGCGTTGTTCGGAATTATTGGGCGTAAAGGGCGCGTAGGCGGTGCGGTAAGTCACCTGTGAAACCTCTGGGCTCAACCCAGAGCCTGCAGGCGAAACTGCCGTGCTGGAGTATGGGAGAGGTGCGTGGAATTCCCGGTGTAGCGGTGAAATGCGTAGATATCGGGAGGAACACCTGTGGCGAAAGCGGCGCACTGGACCATAACTGACGCTGAGGCGCGAAAGCTAGGGGAGCAAACA
>test-seq-2
TGGGGAATTTTGCGCAATGGGGGAAACCCTGACGCAGCAACGCCGCGTGGAGGATGAAGCCCCTTGGGGTGTAAACTCCTTTCGATCGGGACGATTATGACGGTACCGGATGAAGAAGCACCGGCTAACTCTGTGCCAGCAGCCGCGGTAATACAGAGGGTGCAAGCGTTGTTCGGAATTATTGGGCGTAAAGGGTGCGTAGGCGGTGCGGTAAGTCTTTTGTGAAATCTCCGGGCTCAACCCGGAGCCTGCAAGGGAAACTGCCGTGCTTGAGTGTGGGAGAGGTGAGTGGAATTCCCGGTGTAGCGGTGAAATGCGTAGATATCGGGAGGAACACCTGTGGCGAAAGCGGCTCACTGGACCACAACTGACGCTGATGCACGAAAGCTAGGGGAGCAAACA
>test-seq-3
TGGGGAATTTTGCGCAATGGGGGAAACCCTGACGCAGCAACGCCGCGTGGAGGATGAAGTCCCTTGGGACGTAAACTCCTTTCGATCGGGACGATTATGACGGTACCGGAAGAAGAAGCCCCGGCTAACTTCGTGCCAGCAGCCGCGGTAATACGAGGGGGGCGAGCGTTGTTCGGAATTATTGGGCGTAAAGGGCGCGTAGGCGGTCGAATAAGTCTTGTGTGAAATCTTCGGGCTCAACTCGAAGTCTGCATGAGAAACTGTCCGGCTTGAGTGTGGGAGAGGTGAGTGGAATTCCTGGTGTAGCGGTGAAATGCGTAGATATCAGGAGGAACACCTGTGGCGAAAGCGGCTCACTGGACCACAACTGACGCTGATGCGCGAAAGCTAGGGGAGCAAACA
>test-seq-4
TGGGGAATTTTGCGCAATGGGGGAAACCCTGACGCAGCAACGCCGCGTGGAGGATGAAGTCCCTTGGGACGTAAACTCCTTTCGACTGGGAAGATAATGACGGTACCAGTGGAAGAAGCCCCGGCTAACTTCGTGCCAGCAGCCGCGGTAATACGAGGGGGGCGAGCGTTGTTCGGAATTATTGGGCGTAAAGGGCGCGTAGGCGGTGCGGTAAGTCACCTGTGAAACCTCTGGGCTCAACTCAGAGCCTGCAGGCGAAACTGCCGTGCTGGAGGGTGGGAGAGGTGCGTGGAATTCCCGGTGTAGCGGTGAAATGCGTAGATATCGGGAGGAACACCTGTGGCGAAAGCGGCGCACTGGACCACTTCTGACGCTGAGGCGCGAAAGCTAGGGGAGCAAACA
>test-seq-5
TGGGGAATTTTGCGCAATGGGGGAAACCCTGACGCAGCAACGCCGCGTGGAGGATGAAGCCCCTTGGGGTGTAAACTCCTTTCGACCGGGAAAATTATGATGGTACCGGTGGAAGAAGCACCGGCTAACTCTGTGCCAGCAGCCGCGGTAATACAGAGGGTGCGAGCGTTGTTCGGAATTATTGGGCGTAAAGGGCGCGTAGGCGGTGCGGTAAGTCACCTGTGAAATCCCCAGGCTTAACTTGGGGCCTGCAGGCGAAACTGCCGTGCTGGAGGGTGGGAGAGGTGCGTGGAATTCCCGGTGTAGCGGTGAAATGCGTAGATATCGGGAGGAACACCTGTGGCGAAAGCGGCGCACTGGACCACTACTGACGCTGAGGCGCGAAAGCTAGGGGAGCAAACA
>068f2c0a7c0fcf9cef0becb9f166d479"""


def fasta_length_check(form, field):
    if len(field.data) < 1:
        raise ValidationError('Please submit an input sequence')
    if len(field.data) > 500000:
        raise ValidationError('Input sequence must be less than 500000 characters')
    if field.data[0] != '>':
        raise ValidationError('Input sequence must be in fasta format')
    # Count number of fasta headers:
    all_headers = [line for line in field.data.split(
        '\n') if (not len(line) == 0) and (line[0] == '>')]
    # if len(all_headers) != 1:
    #     raise ValidationError('Only one input sequence at a time is allowed')


def identity_check(form, field):
    # Check max value, min value
    if field.data is not None:
        try:
            data_i = int(field.data)
        except:
            return None
        if data_i < 0 or data_i > 100:
            raise ValidationError('Please enter value between 0 and 100')


def cover_check(form, field):
    # Check max value, min value
    if field.data is not None:
        try:
            data_i = int(field.data)
        except:
            return None
        if data_i < 0 or data_i > 100:
            raise ValidationError('Please enter value between 0 and 100')


class BlastSearchForm(FlaskForm):
    sequence = TextAreaField(u'sequence', [fasta_length_check], default=DEFAULT_BLAST_GENE)
    min_identity = IntegerField(u'min_identity', [identity_check], default=97)
    min_qry_cover = IntegerField(u'min_qry_cover', [cover_check], default=100)
    blast_for_seq = SubmitField(u'BLAST')


class BlastResultForm(FlaskForm):
    asv_id = BooleanField(u'asv_id')
    batch_url = app.config['BATCH_SEARCH_URL']
    redirect_url = app.config['REDIRECT_URL']


class ApiSearchForm(FlaskForm):
    gene_sel = SelectMultipleField('gene_sel', choices=[])
    fw_prim_sel = SelectMultipleField('fw_prim_sel', choices=[])
    rv_prim_sel = SelectMultipleField('rv_prim_sel', choices=[])
    search_for_asv = SubmitField(u'Search')


class ApiResultForm(FlaskForm):
    asv_id = BooleanField(u'asv_id')
    batch_url = app.config['BATCH_SEARCH_URL']
    redirect_url = app.config['REDIRECT_URL']
