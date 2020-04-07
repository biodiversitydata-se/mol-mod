from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms import TextAreaField, RadioField, IntegerField, ValidationError
from wtforms.validators import DataRequired


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


DEFAULT_BLAST_GENE = """>test1
TGGGGAATATTGGGCAATGGAGGAAACTCTGACCCAGCGACGCCGCGTGCGGGATGAAGGCCTTCGGGTTGTAAACCGCTTTCAGCAGGGAAGAAGCGAAAGTGACGGTACCTGCAGAAGAAGCACCGGCTAACTATGTGCCAGCAGCCGCGGTAATACATAGGGTGCAAGCGTTGTCCGGAATTATTGGGCGTAAAGAGCTCGTAGGTGGTTCGTCACGTCGGATGTGAAACTCTGGGGCTTAACCCCAGACCTGCATTCGATACGGGCGAGCTTGAGTATGGTAGGGGAGTCTGGAATTCCTGGTGTAGCGGTGGAATGCGCAGATATCAGGAGGAACACCAATGGCGAAGGCAGGACTCTGGGCCATTACTGACACTGAGGAGCGAAAGCGTGGGGAGCGAACA"""


def fasta_length_check(form, field):
    if len(field.data) < 1:
        raise ValidationError('Please submit an input sequence')
    if len(field.data) > 15000:
        raise ValidationError('Input sequence must be less than 15000 characters')
    if field.data[0] != '>':
        raise ValidationError('Input sequence must be in fasta format')
    # Count number of fasta headers:
    all_headers = [line for line in field.data.split(
        '\n') if (not len(line) == 0) and (line[0] == '>')]
    if len(all_headers) != 1:
        raise ValidationError('Only one input sequence at a time is allowed')


def e_val_exponent_check(form, field):
    # Check max value, min value
    # Ignore case when data is not integer which is handled by wtforms
    if field.data is not None:
        try:
            data_i = int(field.data)
        except:
            return None
        if data_i < -256:
            raise ValidationError('Exponent is required to be larger than -256')
        if data_i > 256:
            raise ValidationError('Exponent is required to be smaller than 256')


def e_val_factor_check(form, field):
    # Check max value, min value
    # Ignore case when data is not integer which is handled by wtforms
    if field.data is not None:
        try:
            data_i = int(field.data)
        except:
            return None
        if data_i < 0:
            raise ValidationError('Factor is required to be non-negative')
        if data_i > 9:
            raise ValidationError('Exponent is required to be smaller than 10')


def identity_check(form, field):
    # Check max value, min value
    if field.data is not None:
        try:
            data_i = int(field.data)
        except:
            return None
        if data_i < 0:
            raise ValidationError('Minimum identity is required to be non-negative')
        if data_i > 100:
            raise ValidationError('Minimum identity is required to be smaller than 101')


def aln_length_check(form, field):
    # Check max value, min value
    if field.data is not None:
        try:
            data_i = int(field.data)
        except:
            return None
        if data_i < 0:
            raise ValidationError('Minimum alignment length is required to be non-negative')
        if data_i > 100000:
            raise ValidationError('Minimum alignment length is required to be smaller than 100000')


class BlastFilterForm(FlaskForm):
    sequence = TextAreaField('Sequence', [fasta_length_check], default=DEFAULT_BLAST_GENE)
    blast_algorithm = RadioField(u'Algorithm', choices=[(
        'blastp', 'blastp'), ('blastn', 'blastn')], default='blastp')
    e_value_exponent = IntegerField(u'e_value_exponent', [e_val_exponent_check], default=-5)
    e_value_factor = IntegerField(u'e_value_factor', [e_val_factor_check], default=1)
    min_identity = IntegerField(u'min_identity', [identity_check], default=0)
    min_aln_length = IntegerField(u'min_aln_length', [aln_length_check], default=0)
    submit_view = SubmitField(u'View Results')
