from flask import Blueprint, render_template
from flask_login import login_required, current_user
from ..services.ai_service import bio

main_bp = Blueprint('main_bp', __name__, template_folder='templates')

@main_bp.route('/home')
@login_required
def home():
    sample_goal = 'Finish my outline'
    my_bio = bio(current_user.name, 30, 'Developer', sample_goal)
    return render_template('private/home.html',
                           user=current_user, bio=my_bio)
