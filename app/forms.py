"""
SkillHive - WTForms Form Definitions
======================================
Flask-WTF forms with CSRF protection and server-side validation.
Used for demand creation/editing and application submission.
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField, TextAreaField, SelectField, IntegerField,
    DateField, HiddenField
)
from wtforms.validators import (
    DataRequired, Email, Optional, NumberRange, Length, ValidationError
)


class DemandForm(FlaskForm):
    """
    Form for creating and editing project demands.
    Used by PMO team members to post new resource requirements.
    """
    # ---------- Project Information ----------
    project_name = StringField(
        'Project Name',
        validators=[DataRequired(message='Project name is required'),
                    Length(max=255)]
    )
    project_code = StringField(
        'Project Code',
        validators=[Optional(), Length(max=50)]
    )
    rrd = StringField(
        'RRD',
        validators=[DataRequired(message='RRD is required'),
                    Length(max=255)]
    )

    # ---------- Requirement Details ----------
    # Skills are handled via JavaScript tag input, stored as hidden comma-separated value
    skills = HiddenField(
        'Required Skills',
        validators=[Optional()]
    )
    career_level = SelectField(
        'Career Level',
        choices=[
            ('12', 'CL12 - ASE'),
            ('11', 'CL11 - SSE'),
            ('10', 'CL10 - SE'),
            ('9', 'CL9 - TL'),
            ('8', 'CL8 - AM'),
        ],
        validators=[DataRequired()]
    )
    num_positions = IntegerField(
        'Number of Positions',
        default=1,
        validators=[DataRequired(), NumberRange(min=1, max=100,
                    message='Must be between 1 and 100')]
    )
    start_date = DateField(
        'Start Date',
        validators=[Optional()],
        format='%Y-%m-%d'
    )
    end_date = DateField(
        'End Date',
        validators=[Optional()],
        format='%Y-%m-%d'
    )

    # ---------- Priority ----------
    priority = SelectField(
        'Priority',
        choices=[
            ('critical', '🔴 Critical'),
            ('high', '🟠 High'),
            ('medium', '🟡 Medium'),
            ('low', '🟢 Low'),
        ],
        default='medium',
        validators=[DataRequired()]
    )

    # ---------- Evaluator Information ----------
    evaluator_name = StringField(
        'Evaluator Name',
        validators=[DataRequired(message='Evaluator name is required'),
                    Length(max=255)]
    )
    evaluator_email = StringField(
        'Evaluator Email',
        validators=[DataRequired(message='Evaluator email is required'),
                    Email(message='Please enter a valid email address')]
    )
    evaluator_contact = StringField(
        'Evaluator Contact (Phone)',
        validators=[Optional(), Length(max=50)]
    )

    # ---------- Description ----------
    description = TextAreaField(
        'Job Description',
        validators=[Optional(), Length(max=5000)]
    )
    additional_notes = TextAreaField(
        'Additional Notes',
        validators=[Optional(), Length(max=2000)]
    )

    def validate_end_date(self, field):
        """Ensure end date is after start date if both are provided."""
        if field.data and self.start_date.data:
            if field.data < self.start_date.data:
                raise ValidationError('End date must be after start date.')


class ApplicationForm(FlaskForm):
    """
    Form for resources to apply for evaluation against a demand.
    Includes personal details and one-page resume upload (DOCX/PPTX).
    """
    applicant_name = StringField(
        'Full Name',
        validators=[DataRequired(message='Your name is required'),
                    Length(max=255)]
    )
    enterprise_id = StringField(
        'Enterprise ID',
        validators=[DataRequired(message='Enterprise ID is required'),
                    Length(max=50)]
    )
    current_project = StringField(
        'Current Project',
        validators=[Optional(), Length(max=255)]
    )
    years_of_experience = IntegerField(
        'Years of Experience',
        validators=[DataRequired(message='Years of experience is required'),
                    NumberRange(min=0, max=50, message='Must be between 0 and 50')]
    )
    skills_text = TextAreaField(
        'Your Key Skills (comma-separated)',
        validators=[Optional(), Length(max=1000)]
    )
    resume = FileField(
        'Upload One-Page Resume (DOCX or PPTX)',
        validators=[
            FileAllowed(['docx', 'pptx'], 'Only .docx and .pptx files are allowed!')
        ]
    )


class ApplicationStatusForm(FlaskForm):
    """
    Form for PMO/Evaluator to update application status.
    Supports the workflow: Applied → Under Evaluation → Selected / Rejected
    """
    status = SelectField(
        'New Status',
        choices=[
            ('applied', '📋 Applied'),
            ('under_evaluation', '🔍 Under Evaluation'),
            ('selected', '✅ Selected'),
            ('rejected', '❌ Rejected'),
        ],
        validators=[DataRequired()]
    )
    remarks = TextAreaField(
        'Remarks / Feedback',
        validators=[Optional(), Length(max=2000)]
    )
