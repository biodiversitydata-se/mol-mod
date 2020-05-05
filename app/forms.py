from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, StringField, SubmitField
from wtforms import TextAreaField, ValidationError
from wtforms.validators import InputRequired

DEFAULT_BLAST_GENE = """>test-seq-1
GCGCGAAAACTTCACACTGCAGGAAACTGTGATGAGGGAACTCCAAGTGCATCCACTATGTGGATGCTTTTTTTGACTATTAATCGGTCAACGAATAAGGGCTGGGAAAGACCGGTGCCAGCCGCCGCGGTAATACCGGCAGCTCAAGTGGTCGTCGCTTTTATTGGGCCTAAAACGTCCGTAGCCTGTTTGGTAAATCTGTGGGTAAATCAACCAGCTTAACTGGTTGAATTCTGCAGAGACTGCCAGACTAGGGACCGGGAGAGGTGTGGGGTACTCTAGGGGTAGGGGTAAAATCCTGTCATCCTTAGAGGACCACCAGTTGCGAAGGCGCCACACTGGAACGGATCCGACGGTCAGGGACGAAGCCTAGGGGCACGAACC
>test-seq-2
GCGCGAAAACTTCACACTGCAGGAAACTGTGATGAGGGAACTCCAAGTGACTGCACATTGTGTAGCCTTTTCTTTACTATTAATCGGTATTGGAATAAGGGCTGGGAAAGACCGGTGCCAGCCGCCGCGGTAATACCGGCAGCTCAAGTGGTCGTCGCTTTTATTGGGCCTAAAACGTCCGTAGCCTGTTTGGTAAATCTGTGGGTAAATCAACCAGCTTAACTGGTTGAATTCTGCAGAGACTGCCAGACTAGGGACCGGGAGAGGTGTGGGGTACTCTAGGGGTAGGGGTAAAATCCTGTCATCCTTAGAGGACCACCAGTTGCGAAGGCGCCACACTGGAACGGATCCGACGGTCAGGGACGAAGCCTAGGGGCACGAACC"""


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
            raise ValidationError('Value between 0-100 expected')


def cover_check(form, field):
    # Check max value, min value
    if field.data is not None:
        try:
            data_i = int(field.data)
        except:
            return None
        if data_i < 0 or data_i > 100:
            raise ValidationError('Value between 0-100 expected')


class BlastSearchForm(FlaskForm):
    sequence = TextAreaField(u'sequence', [fasta_length_check], default=DEFAULT_BLAST_GENE)
    min_identity = IntegerField(u'min_identity', [identity_check], default=100)
    min_qry_cover = IntegerField(u'min_qry_cover', [cover_check], default=100)
    blast_for_seq = SubmitField(u'BLAST')


class BlastResultForm(FlaskForm):
    asvid = BooleanField(u'asvid')
    show_occur = SubmitField(u'Show occurrences')
