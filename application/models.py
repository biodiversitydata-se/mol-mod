#!/usr/bin/env python

# Std lib
from . import db

# Observation of specific ASV in specific analysis (i.e. ENA sample)
# [Note that new primer set -> new ENA 'sample']
class Observation(db.Model):
    __tablename__ = 'observation'
    asv_id = db.Column(db.Integer, db.ForeignKey('asv.id'), primary_key=True)
    # i.e. link to ENA record
    ena_sample_id = db.Column(db.String, primary_key=True)
    # Metadata that are not (yet) searchable in atlas:
    primer_fw_name = db.Column(db.String)
    primer_rv_name = db.Column(db.String)
    primer_fw_sequence = db.Column(db.String)
    primer_rv_sequence = db.Column(db.String)
    # Filtering, denoising etc. - could be our pipeline
    processing_description = db.Column(db.Text)
    # Need to update after successful import into atlas
    atlas_dataset_id = db.Column(db.Text)
    # Darwin core file to be submitted to atlas
    dwca_link = db.Column(db.String)
    # Fix later:
    #def __repr__(self):
    #    return '<Observation {}>'.format(self.id)

# Amplicon Sequence Variant (ASV)
class ASV(db.Model):
    __tablename__ = 'asv'
    # Replace with Checksum?
    id = db.Column(db.Integer, primary_key=True)
    # Unique
    sequence = db.Column(db.Text)
    genomic_region = db.Column(db.String)
    # Date/time of first addition to ASV list
    date = db.Column(db.DateTime)
    # Filtering, denoising etc. - could be pipeline
    processing_description = db.Column(db.Text)
    def __repr__(self):
        return '<ASV {}>'.format(self.id)

# Taxonomic annotation of ASV
class Annotation(db.Model):
    __tablename__ = 'annotation'
    event_id = db.Column(db.Integer, db.ForeignKey('annotation_event.id'), primary_key=True)
    asv_id = db.Column(db.Integer, db.ForeignKey('asv.id'), primary_key=True)
    current = db.Column(db.Boolean)
    kingdom = db.Column(db.String)
    phylum = db.Column(db.String)
    classs = db.Column(db.String)
    order = db.Column(db.String)
    family = db.Column(db.String)
    genus = db.Column(db.String)
    specific_epithet = db.Column(db.String)
    # Needed?
    subspecific_epithet = db.Column(db.String)
    otu = db.Column(db.String)
    # Probability, similarity...?
    annotation_score = db.Column(db.String)
    # Explanation of manual edit by conbtributor
    annotation_note = db.Column(db.String)
    # Fix later:
    #def __repr__(self):
    #    return '<Observation {}>'.format(self.id)

# Annotation of whole dataset(s)
class AnnotationEvent(db.Model):
    __tablename__ = 'annotation_event'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime)
    # Initial: contributor or SBDI,
    # or regular SBDI update for specific group (e.g. prokaryotes)
    type = db.Column(db.String)
    # E.g. SILVA SSU
    reference_db = db.Column(db.String)
    # E.g. 138
    reference_db_release = db.Column(db.String)
    # E.g. IDTAXA
    algorithm = db.Column(db.String)
    # Detailed description of algorithm and settings
    method_description = db.Column(db.Text)

# Test
class User(db.Model):
    """Model for user accounts."""

    __tablename__ = 'users'
    id = db.Column(db.Integer,
                   primary_key=True)
    username = db.Column(db.String(64),
                         index=False,
                         unique=True,
                         nullable=False)
    email = db.Column(db.String(80),
                      index=True,
                      unique=True,
                      nullable=False)
    created = db.Column(db.DateTime,
                        index=False,
                        unique=False,
                        nullable=False)
    bio = db.Column(db.Text,
                    index=False,
                    unique=False,
                    nullable=True)
    admin = db.Column(db.Boolean,
                      index=False,
                      unique=False,
                      nullable=False)

    def __repr__(self):
        return '<User {}>'.format(self.username)
