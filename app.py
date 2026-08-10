import os
import datetime
import queue
from functools import wraps
from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
import jwt
import bcrypt
from werkzeug.security import check_password_hash
from dotenv import load_dotenv
import certifi

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'super-secret-key-change-me')
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = os.getenv('DB_NAME', 'eafc_tournament')

# MongoDB Connection
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
db = client[DB_NAME]

# Server-Sent Events (SSE) listener list for real-time notifications
sse_listeners = []

def notify_update():
    for q in list(sse_listeners):
        try:
            q.put("update")
        except Exception as e:
            print("Failed to notify queue:", e)

# Audit Log Helper
def log_action(username, action, details):
    try:
        db.audit_logs.insert_one({
            'username': username,
            'action': action,
            'details': details,
            'timestamp': datetime.datetime.utcnow().isoformat()
        })
    except Exception as e:
        print("Logging failed:", e)

# Decorator for admin routes
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            try:
                token = request.headers['Authorization'].split(" ")[1] # Bearer Token
            except IndexError:
                return jsonify({'message': 'Token format is invalid!'}), 401
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = db.users.find_one({'username': data['username']})
            if not current_user:
                raise Exception("User not found")
        except Exception as e:
            return jsonify({'message': 'Token is invalid!'}), 401

        return f(current_user, *args, **kwargs)
    return decorated

# --- HOME ROUTE ---
@app.route('/')
def home():
    return render_template('index.html')

# --- AUTHENTICATION ROUTES ---
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400

    try:
        user = db.users.find_one({'username': username})
        if user:
            stored_pwd = user['password']
            if stored_pwd.startswith('$2b$') or stored_pwd.startswith('$2a$'):
                is_valid = bcrypt.checkpw(password.encode('utf-8'), stored_pwd.encode('utf-8'))
            elif stored_pwd.startswith('scrypt:') or stored_pwd.startswith('pbkdf2:'):
                is_valid = check_password_hash(stored_pwd, password)
            else:
                is_valid = (stored_pwd == password)

            if is_valid:
                token = jwt.encode({
                    'username': user['username'],
                    'role': user.get('role', 'admin'),
                    'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
                }, app.config['SECRET_KEY'], algorithm="HS256")
                
                return jsonify({
                    'token': token,
                    'username': user['username'],
                    'role': user.get('role', 'admin')
                })
        return jsonify({'message': 'Invalid credentials'}), 401
    except Exception as e:
        return jsonify({'message': f'Database Error: {str(e)}'}), 500

@app.route('/api/user/password', methods=['PUT'])
@token_required
def change_password(current_user):
    data = request.get_json(silent=True) or {}
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not old_password or not new_password:
        return jsonify({'message': 'Both old and new passwords are required'}), 400

    stored_pwd = current_user['password']
    is_valid = False
    
    if stored_pwd.startswith('$2b$') or stored_pwd.startswith('$2a$'):
        is_valid = bcrypt.checkpw(old_password.encode('utf-8'), stored_pwd.encode('utf-8'))
    elif stored_pwd.startswith('scrypt:') or stored_pwd.startswith('pbkdf2:'):
        is_valid = check_password_hash(stored_pwd, old_password)
    else:
        is_valid = (stored_pwd == old_password)

    if not is_valid:
        return jsonify({'message': 'Old password incorrect'}), 400

    hashed_new = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    db.users.update_one({'_id': current_user['_id']}, {'$set': {'password': hashed_new}})
    
    log_action(current_user['username'], 'CHANGE_PASSWORD', "Changed admin account password.")
    return jsonify({'message': 'Password updated successfully'})

# --- ADMIN USER MANAGEMENT (SUPERADMIN ONLY) ---
@app.route('/api/users', methods=['GET'])
@token_required
def get_users(current_user):
    if current_user.get('role') != 'superadmin':
        return jsonify({'message': 'Unauthorized'}), 403
    try:
        users = list(db.users.find({}, {'password': 0}))
        for u in users:
            u['_id'] = str(u['_id'])
        return jsonify(users)
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@app.route('/api/users', methods=['POST'])
@token_required
def create_user(current_user):
    if current_user.get('role') != 'superadmin':
        return jsonify({'message': 'Unauthorized'}), 403
    
    data = request.get_json(silent=True) or {}
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'admin')

    if not username or not password:
        return jsonify({'message': 'Username and password required'}), 400

    try:
        if db.users.find_one({'username': username}):
            return jsonify({'message': 'Username already exists'}), 400
        
        hashed_pwd = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        db.users.insert_one({
            'username': username,
            'password': hashed_pwd,
            'role': role
        })
        
        log_action(current_user['username'], 'CREATE_ADMIN', f"Created new admin user: '{username}'.")
        return jsonify({'message': 'User created successfully'})
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@app.route('/api/users/<user_id>', methods=['DELETE'])
@token_required
def delete_user(current_user, user_id):
    if current_user.get('role') != 'superadmin':
        return jsonify({'message': 'Unauthorized'}), 403
    try:
        target = db.users.find_one({'_id': ObjectId(user_id)})
        if not target:
            return jsonify({'message': 'User not found'}), 404
        if target['username'] == current_user['username']:
            return jsonify({'message': 'Cannot delete yourself'}), 400

        db.users.delete_one({'_id': ObjectId(user_id)})
        log_action(current_user['username'], 'DELETE_ADMIN', f"Deleted admin user: '{target['username']}'.")
        return jsonify({'message': 'User deleted successfully'})
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# --- TOURNAMENT SETTINGS ---
@app.route('/api/settings', methods=['GET'])
def get_settings():
    settings = db.settings.find_one({'type': 'general'})
    if not settings:
        settings = {'type': 'general', 'competition_name': 'ABC CUP TOURNAMENT'}
        db.settings.insert_one(settings)
    settings['_id'] = str(settings['_id'])
    return jsonify(settings)

@app.route('/api/settings', methods=['PUT'])
@token_required
def update_settings(current_user):
    data = request.get_json(silent=True) or {}
    comp_name = data.get('competition_name')
    if comp_name:
        db.settings.update_one({'type': 'general'}, {'$set': {'competition_name': comp_name}}, upsert=True)
        log_action(current_user['username'], 'UPDATE_SETTINGS', f"Updated tournament name to '{comp_name}'.")
        notify_update()
        return jsonify({'message': 'Settings updated successfully'})
    return jsonify({'message': 'No settings provided'}), 400

# --- GROUP STAGE API ROUTES ---
@app.route('/api/groups', methods=['GET'])
def get_groups():
    include_hidden = request.args.get('include_hidden', 'false').lower() == 'true'
    query = {} if include_hidden else {'isHidden': {'$ne': True}}
    
    groups = list(db.groups.find(query))
    for g in groups:
        g['_id'] = str(g['_id'])
        matches_query = {'groupId': g['_id']}
        if not include_hidden:
            matches_query['isHidden'] = {'$ne': True}
            
        matches = list(db.matches.find(matches_query))
        for m in matches:
            m['_id'] = str(m['_id'])
            if 'status' in m:
                status = m['status']
                if 'isLive' not in m:
                    m['isLive'] = (status == 'live')
                if 'isFinished' not in m:
                    m['isFinished'] = (status == 'finished')
            
            if 'isLive' not in m:
                m['isLive'] = False
            if 'isFinished' not in m:
                m['isFinished'] = False

        standings = {}
        for team in g.get('teams', []):
            standings[team['id']] = {
                'id': team['id'],
                'name': team['name'],
                'code': team.get('code', ''),
                'logo': team.get('logo', ''),
                'played': 0, 'won': 0, 'drawn': 0, 'lost': 0,
                'gf': 0, 'ga': 0, 'gd': 0, 'pts': 0, 'last5': []
            }

        for m in matches:
            if m.get('isFinished') or m.get('status') == 'finished':
                t1_id = m['team1']['id']
                t2_id = m['team2']['id']
                s1 = m.get('score1', 0)
                s2 = m.get('score2', 0)
                
                if t1_id in standings and t2_id in standings:
                    standings[t1_id]['played'] += 1
                    standings[t2_id]['played'] += 1
                    standings[t1_id]['gf'] += s1
                    standings[t1_id]['ga'] += s2
                    standings[t2_id]['gf'] += s2
                    standings[t2_id]['ga'] += s1
                    
                    if s1 > s2:
                        standings[t1_id]['won'] += 1
                        standings[t1_id]['pts'] += 3
                        standings[t1_id]['last5'].append('W')
                        standings[t2_id]['lost'] += 1
                        standings[t2_id]['last5'].append('L')
                    elif s2 > s1:
                        standings[t2_id]['won'] += 1
                        standings[t2_id]['pts'] += 3
                        standings[t2_id]['last5'].append('W')
                        standings[t1_id]['lost'] += 1
                        standings[t1_id]['last5'].append('L')
                    else:
                        standings[t1_id]['drawn'] += 1
                        standings[t1_id]['pts'] += 1
                        standings[t1_id]['last5'].append('D')
                        standings[t2_id]['drawn'] += 1
                        standings[t2_id]['pts'] += 1
                        standings[t2_id]['last5'].append('D')

        standings_list = list(standings.values())
        for s in standings_list:
            s['gd'] = s['gf'] - s['ga']
            s['last5'] = s['last5'][-5:]

        from functools import cmp_to_key
        def compare_teams(a, b):
            if a['pts'] != b['pts']:
                return b['pts'] - a['pts']
            if a['gd'] != b['gd']:
                return b['gd'] - a['gd']
            if a['gf'] != b['gf']:
                return b['gf'] - a['gf']
            return -1 if a['name'].lower() < b['name'].lower() else 1

        standings_list.sort(key=cmp_to_key(compare_teams))
        g['standings'] = standings_list
        g['matches'] = matches

    return jsonify(groups)

@app.route('/api/groups', methods=['POST'])
@token_required
def create_group(current_user):
    data = request.get_json(silent=True) or {}
    name = data.get('name')
    teams_input = data.get('teams', [])

    if not name or not teams_input:
        return jsonify({'message': 'Group name and teams are required'}), 400

    teams = []
    for index, t_name in enumerate(teams_input):
        t_clean = str(t_name).strip()
        if t_clean:
            teams.append({
                'id': f"t_{ObjectId()}",
                'name': t_clean,
                'logo': f"https://api.dicebear.com/7.x/identicon/svg?seed={t_clean}"
            })

    group_doc = {
        'name': name,
        'teams': teams,
        'isHidden': False,
        'createdAt': datetime.datetime.utcnow().isoformat()
    }
    
    result = db.groups.insert_one(group_doc)
    group_id = str(result.inserted_id)

    log_action(current_user['username'], 'CREATE_GROUP', f"Created Group Stage '{name}' with {len(teams)} teams.")
    notify_update()
    return jsonify({'message': 'Group created successfully', 'id': group_id})

@app.route('/api/groups/<group_id>', methods=['PUT'])
@token_required
def update_group(current_user, group_id):
    data = request.get_json(silent=True) or {}
    update_data = {}
    if 'name' in data:
        update_data['name'] = data['name']
    if 'teams' in data:
        update_data['teams'] = data['teams']
    if 'isHidden' in data:
        update_data['isHidden'] = data['isHidden']

    if not update_data:
        return jsonify({'message': 'No valid fields provided for update'}), 400

    db.groups.update_one({'_id': ObjectId(group_id)}, {'$set': update_data})
    
    if 'isHidden' in data:
        action = 'RESTORE_GROUP' if not data['isHidden'] else 'HIDE_GROUP'
        log_action(current_user['username'], action, f"Updated Group '{group_id}' visibility status.")
    else:
        log_action(current_user['username'], 'EDIT_GROUP', f"Updated Group details for ID: {group_id}.")
        
    notify_update()
    return jsonify({'message': 'Group updated successfully'})

@app.route('/api/groups/<group_id>', methods=['DELETE'])
@token_required
def delete_group(current_user, group_id):
    is_permanent = request.args.get('permanent', 'false').lower() == 'true'
    group = db.groups.find_one({'_id': ObjectId(group_id)})
    if not group:
        return jsonify({'message': 'Group not found'}), 404

    if is_permanent:
        if current_user.get('role') != 'superadmin':
            return jsonify({'message': 'Superadmin privileges required'}), 403
        db.groups.delete_one({'_id': ObjectId(group_id)})
        db.matches.delete_many({'groupId': group_id})
        log_action(current_user['username'], 'DELETE_GROUP', f"Permanently deleted Group '{group['name']}' and its matches.")
    else:
        db.groups.update_one({'_id': ObjectId(group_id)}, {'$set': {'isHidden': True}})
        log_action(current_user['username'], 'HIDE_GROUP', f"Soft-deleted (hid) Group '{group['name']}'.")

    notify_update()
    return jsonify({'message': 'Group deleted successfully'})

# --- MATCH MANAGEMENT API ROUTES ---
@app.route('/api/matches/start', methods=['POST'])
@token_required
def start_match(current_user):
    data = request.get_json(silent=True) or {}
    group_id = data.get('groupId')
    home_team_id = data.get('homeTeamId') or data.get('homeId')
    away_team_id = data.get('awayTeamId') or data.get('awayId')

    if not group_id or not home_team_id or not away_team_id:
        return jsonify({'message': 'groupId, homeTeamId, and awayTeamId are required'}), 400

    group = db.groups.find_one({'_id': ObjectId(group_id)})
    if not group:
        return jsonify({'message': 'Group not found'}), 404

    home_team = next((t for t in group.get('teams', []) if t['id'] == home_team_id), None)
    away_team = next((t for t in group.get('teams', []) if t['id'] == away_team_id), None)

    if not home_team or not away_team:
        return jsonify({'message': 'Teams not found in group'}), 404

    existing_finished = db.matches.find_one({
        'groupId': group_id,
        'team1.id': home_team_id,
        'team2.id': away_team_id,
        'isHidden': {'$ne': True},
        '$or': [{'isFinished': True}, {'status': 'finished'}]
    })

    if existing_finished:
        return jsonify({
            'message': f"Pertandingan {home_team['name']} (Home) vs {away_team['name']} (Away) sudah pernah diselesaikan!"
        }), 400

    existing_unfinished = db.matches.find_one({
        'groupId': group_id,
        'team1.id': home_team_id,
        'team2.id': away_team_id,
        'isHidden': {'$ne': True}
    })

    if existing_unfinished:
        db.matches.update_many({'isLive': True}, {'$set': {'isLive': False, 'status': 'scheduled'}})
        db.matches.update_many({'status': 'live'}, {'$set': {'isLive': False, 'status': 'scheduled'}})
        db.matches.update_one({'_id': existing_unfinished['_id']}, {'$set': {'isLive': True, 'status': 'live'}})
        
        log_action(current_user['username'], 'RESUME_MATCH', f"Resumed Live Match: {home_team['name']} vs {away_team['name']}.")
        notify_update()
        return jsonify({'message': 'Live match resumed', 'id': str(existing_unfinished['_id'])})

    db.matches.update_many({'isLive': True}, {'$set': {'isLive': False, 'status': 'scheduled'}})
    db.matches.update_many({'status': 'live'}, {'$set': {'isLive': False, 'status': 'scheduled'}})

    match_count = db.matches.count_documents({})
    match_doc = {
        'groupId': group_id,
        'groupName': group['name'],
        'team1': home_team,
        'team2': away_team,
        'score1': 0,
        'score2': 0,
        'isLive': True,
        'isFinished': False,
        'isHidden': False,
        'status': 'live',
        'playOrder': match_count,
        'startedAt': datetime.datetime.utcnow().isoformat()
    }

    result = db.matches.insert_one(match_doc)
    match_id = str(result.inserted_id)

    log_action(current_user['username'], 'START_MATCH', f"Started Live Match: {home_team['name']} vs {away_team['name']} in {group['name']}.")
    notify_update()
    return jsonify({'message': 'Live match started', 'id': match_id})

@app.route('/api/matches/<match_id>', methods=['PUT'])
@token_required
def update_match(current_user, match_id):
    data = request.get_json(silent=True) or {}
    update_fields = {}
    if 'score1' in data:
        update_fields['score1'] = int(data['score1'])
    if 'score2' in data:
        update_fields['score2'] = int(data['score2'])
    if 'isLive' in data:
        update_fields['isLive'] = bool(data['isLive'])
    if 'isFinished' in data:
        update_fields['isFinished'] = bool(data['isFinished'])
    if 'isHidden' in data:
        update_fields['isHidden'] = bool(data['isHidden'])

    if not update_fields:
        return jsonify({'message': 'No valid fields to update'}), 400

    match = db.matches.find_one({'_id': ObjectId(match_id)})
    if not match:
        return jsonify({'message': 'Match not found'}), 404

    db.matches.update_one({'_id': ObjectId(match_id)}, {'$set': update_fields})

    if 'score1' in data or 'score2' in data:
        s1 = update_fields.get('score1', match.get('score1', 0))
        s2 = update_fields.get('score2', match.get('score2', 0))
        log_action(current_user['username'], 'UPDATE_SCORE', f"Updated score for {match['team1']['name']} vs {match['team2']['name']} to {s1}-{s2}.")

    if 'isHidden' in data:
        action = 'RESTORE_MATCH' if not data['isHidden'] else 'HIDE_MATCH'
        log_action(current_user['username'], action, f"Updated visibility for match: {match['team1']['name']} vs {match['team2']['name']}.")

    notify_update()
    return jsonify({'message': 'Match updated successfully'})

@app.route('/api/matches/<match_id>/status', methods=['PUT'])
@token_required
def set_match_status(current_user, match_id):
    data = request.get_json(silent=True) or {}
    is_finished = data.get('isFinished', True)
    
    match = db.matches.find_one({'_id': ObjectId(match_id)})
    if not match:
        return jsonify({'message': 'Match not found'}), 404

    db.matches.update_one({'_id': ObjectId(match_id)}, {
        '$set': {
            'isLive': False,
            'isFinished': is_finished,
            'status': 'finished' if is_finished else 'scheduled',
            'finishedAt': datetime.datetime.utcnow().isoformat()
        }
    })
    
    status_str = "Finished" if is_finished else "Updated Status"
    log_action(current_user['username'], 'FINISH_MATCH', f"Set Match status to '{status_str}': {match['team1']['name']} ({match.get('score1',0)}) vs {match['team2']['name']} ({match.get('score2',0)}).")
    
    notify_update()
    return jsonify({'message': f'Match marked as {status_str}'})

@app.route('/api/matches/<match_id>/reset', methods=['POST', 'DELETE'])
@token_required
def reset_match(current_user, match_id):
    is_permanent = request.args.get('permanent', 'false').lower() == 'true'
    match = db.matches.find_one({'_id': ObjectId(match_id)})
    if not match:
        return jsonify({'message': 'Match not found'}), 404

    is_live = match.get('isLive', False) or match.get('status') == 'live'

    if is_permanent or is_live:
        if not is_live and current_user.get('role') != 'superadmin':
            return jsonify({'message': 'Superadmin privileges required to delete match history'}), 403

        db.matches.delete_one({'_id': ObjectId(match_id)})
        
        if is_live:
            log_action(current_user['username'], 'CANCEL_MATCH', f"Cancelled active live match: {match['team1']['name']} vs {match['team2']['name']}.")
        else:
            log_action(current_user['username'], 'RESET_MATCH', f"Permanently reset/deleted match result: {match['team1']['name']} vs {match['team2']['name']}.")
    else:
        db.matches.update_one({'_id': ObjectId(match_id)}, {'$set': {'isHidden': True}})
        log_action(current_user['username'], 'HIDE_MATCH', f"Soft-deleted (hid) match: {match['team1']['name']} vs {match['team2']['name']}.")

    notify_update()
    return jsonify({'message': 'Match reset successfully'})

@app.route('/api/matches/reorder', methods=['PUT'])
@token_required
def reorder_matches(current_user):
    if current_user.get('role') != 'superadmin':
        return jsonify({'message': 'Unauthorized'}), 403
        
    data = request.get_json(silent=True) or {}
    order = data.get('order', [])
    
    for idx, match_id in enumerate(order):
        db.matches.update_one({'_id': ObjectId(match_id)}, {'$set': {'playOrder': idx}})

    log_action(current_user['username'], 'REORDER_MATCHES', "Reordered the match history sequence.")
    notify_update()
    return jsonify({'message': 'Matches reordered successfully'})

# --- AUDIT LOGS ---
@app.route('/api/logs', methods=['GET'])
@token_required
def get_logs(current_user):
    if current_user.get('role') != 'superadmin':
        return jsonify({'message': 'Unauthorized'}), 403
    try:
        logs = list(db.audit_logs.find().sort('timestamp', -1).limit(100))
        for l in logs:
            l['_id'] = str(l['_id'])
        return jsonify(logs)
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# --- REALTIME SSE ---
@app.route('/api/events')
def sse_events():
    def event_stream():
        q = queue.Queue()
        sse_listeners.append(q)
        try:
            yield "data: connected\n\n"
            while True:
                msg = q.get()
                yield f"data: {msg}\n\n"
        except GeneratorExit:
            pass
        finally:
            if q in sse_listeners:
                sse_listeners.remove(q)

    return Response(event_stream(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
