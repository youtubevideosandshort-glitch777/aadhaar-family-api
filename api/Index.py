from flask import Flask, request, jsonify, Response
import requests
import json
from datetime import datetime
import re

app = Flask(__name__)

# Enable CORS
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response

@app.route('/', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api', methods=['GET', 'POST', 'OPTIONS'])
def home():
    # Handle preflight
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Get parameters
        if request.method == 'GET':
            number = request.args.get('number')
            format_type = request.args.get('format', 'json')
            pretty = request.args.get('pretty', 'false').lower() == 'true'
        else:  # POST
            data = request.get_json() or {}
            number = data.get('number') or request.args.get('number')
            format_type = data.get('format', 'json')
            pretty = data.get('pretty', False)
        
        # Validate Aadhaar number
        if not number:
            return jsonify({
                'success': False,
                'error': 'Aadhaar number is required',
                'usage': {
                    'example': '/?number=691871998983',
                    'methods': ['GET', 'POST']
                }
            }), 400
        
        # Validate format (12 digits)
        if not re.match(r'^\d{12}$', number):
            return jsonify({
                'success': False,
                'error': 'Invalid Aadhaar number. Must be 12 digits.',
                'example': '691871998983'
            }), 400
        
        print(f"[{datetime.now().isoformat()}] Fetching data for: {number}")
        
        # Call original API
        api_url = f"https://aadharfamily.razaisback509.workers.dev?number={number}"
        response = requests.get(api_url, timeout=30)
        data = response.json()
        
        if data.get('status') == True and data.get('result'):
            result = data['result']
            
            # Process family members
            family_members = result.get('family_data', {}).get('pd', {}).get('memberDetailsList', [])
            
            formatted_members = []
            for member in family_members:
                formatted_members.append({
                    'name': member.get('memberName', 'N/A'),
                    'relationship': member.get('releationship_name', 'N/A'),
                    'relationshipCode': member.get('relationship_code', 'N/A'),
                    'memberId': member.get('memberId', 'N/A'),
                    'hasAadhaar': member.get('uid') == 'Yes'
                })
            
            # Find head of family
            head = None
            for member in family_members:
                if member.get('releationship_name') == 'SELF':
                    head = {
                        'name': member.get('memberName', 'N/A'),
                        'memberId': member.get('memberId', 'N/A')
                    }
                    break
            
            # Build response
            final_response = {
                'success': True,
                'data': {
                    'aadhaar': result.get('aadhaar'),
                    'rationCardNumber': result.get('ration_card_number'),
                    'familyDetails': {
                        'address': result.get('family_data', {}).get('pd', {}).get('address', 'N/A'),
                        'district': result.get('family_data', {}).get('pd', {}).get('homeDistName', 'N/A'),
                        'districtCode': result.get('family_data', {}).get('pd', {}).get('districtCode', 'N/A'),
                        'state': result.get('family_data', {}).get('pd', {}).get('homeStateName', 'N/A'),
                        'stateCode': result.get('family_data', {}).get('pd', {}).get('homeStateCode', 'N/A'),
                        'scheme': result.get('family_data', {}).get('pd', {}).get('schemeName', 'N/A'),
                        'schemeId': result.get('family_data', {}).get('pd', {}).get('schemeId', 'N/A'),
                        'fpsId': result.get('family_data', {}).get('pd', {}).get('fpsId', 'N/A')
                    },
                    'headOfFamily': head,
                    'familyMembers': formatted_members,
                    'totalMembers': len(formatted_members)
                },
                'metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'cached': result.get('from_cache', False),
                    'cachedAt': result.get('cached_at') or result.get('_cached_at')
                }
            }
            
            # Handle different formats
            if format_type == 'text':
                text_output = format_as_text(final_response)
                return Response(text_output, mimetype='text/plain')
            
            if format_type == 'html':
                html_output = format_as_html(final_response, number)
                return Response(html_output, mimetype='text/html')
            
            if format_type == 'csv':
                csv_output = format_as_csv(final_response)
                return Response(
                    csv_output,
                    mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename=aadhaar_family_{number}.csv'}
                )
            
            # Default: JSON
            if pretty:
                return jsonify(final_response), 200
            else:
                return json.dumps(final_response), 200, {'Content-Type': 'application/json'}
        
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to fetch family data',
                'details': data
            }), 400
            
    except requests.Timeout:
        return jsonify({
            'success': False,
            'error': 'Request timeout. API took too long to respond.'
        }), 504
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500

def format_as_text(data):
    """Format response as plain text"""
    output = []
    output.append("=== AADHAAR FAMILY INFORMATION ===")
    output.append("")
    output.append(f"Aadhaar Number: {data['data'].get('aadhaar', 'N/A')}")
    output.append(f"Ration Card: {data['data'].get('rationCardNumber', 'N/A')}")
    output.append(f"Total Members: {data['data'].get('totalMembers', 0)}")
    output.append("")
    
    family_details = data['data'].get('familyDetails', {})
    output.append("--- FAMILY DETAILS ---")
    output.append(f"Address: {family_details.get('address', 'N/A')}")
    output.append(f"District: {family_details.get('district', 'N/A')}")
    output.append(f"State: {family_details.get('state', 'N/A')}")
    output.append(f"Scheme: {family_details.get('scheme', 'N/A')}")
    output.append("")
    
    output.append("--- FAMILY MEMBERS ---")
    for idx, member in enumerate(data['data'].get('familyMembers', []), 1):
        output.append(f"\n{idx}. {member['name']}")
        output.append(f"   Relationship: {member['relationship']}")
        output.append(f"   Aadhaar Linked: {'Yes' if member['hasAadhaar'] else 'No'}")
    
    return '\n'.join(output)

def format_as_html(data, aadhaar):
    """Format response as HTML"""
    members = data['data'].get('familyMembers', [])
    family_details = data['data'].get('familyDetails', {})
    head = data['data'].get('headOfFamily', {})
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aadhaar Family - {aadhaar}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ 
            max-width: 900px; 
            margin: 0 auto; 
            background: white; 
            border-radius: 20px; 
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        h1 {{ 
            color: #333; 
            border-bottom: 3px solid #667eea;
            padding-bottom: 15px;
            margin-bottom: 25px;
        }}
        .grid {{ 
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 15px; 
            margin: 20px 0;
        }}
        .card {{ 
            padding: 15px; 
            background: #f8f9fa; 
            border-radius: 10px;
        }}
        .card strong {{ 
            color: #667eea; 
            display: block;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 5px;
        }}
        .member {{ 
            background: #f8f9fa;
            padding: 15px 20px;
            margin: 10px 0;
            border-radius: 10px;
            border-left: 4px solid #667eea;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .member-name {{ font-weight: 600; font-size: 18px; }}
        .member-relation {{ color: #666; font-size: 14px; }}
        .badge {{
            display: inline-block;
            padding: 4px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }}
        .badge-yes {{ background: #28a745; color: white; }}
        .badge-no {{ background: #dc3545; color: white; }}
        .head-badge {{ 
            background: #ffc107; 
            padding: 2px 12px; 
            border-radius: 12px; 
            font-size: 11px; 
            font-weight: 700;
            margin-left: 10px;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
            text-align: center;
            color: #888;
            font-size: 14px;
        }}
        @media (max-width: 600px) {{
            .grid {{ grid-template-columns: 1fr; }}
            .member {{ flex-direction: column; align-items: flex-start; gap: 8px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏠 Aadhaar Family Information</h1>
        
        <div class="grid">
            <div class="card">
                <strong>Aadhaar Number</strong>
                {data['data'].get('aadhaar', 'N/A')}
            </div>
            <div class="card">
                <strong>Ration Card</strong>
                {data['data'].get('rationCardNumber', 'N/A')}
            </div>
            <div class="card">
                <strong>Total Members</strong>
                {data['data'].get('totalMembers', 0)}
            </div>
            <div class="card">
                <strong>Status</strong>
                {'Cached' if data['metadata'].get('cached') else 'Fresh'}
            </div>
        </div>

        <h2>📍 Address Details</h2>
        <div class="grid">
            <div class="card">
                <strong>Address</strong>
                {family_details.get('address', 'N/A')}
            </div>
            <div class="card">
                <strong>District</strong>
                {family_details.get('district', 'N/A')}
            </div>
            <div class="card">
                <strong>State</strong>
                {family_details.get('state', 'N/A')}
            </div>
            <div class="card">
                <strong>Scheme</strong>
                {family_details.get('scheme', 'N/A')}
            </div>
        </div>

        <h2>👨‍👩‍👧‍👦 Family Members</h2>
'''
    
    for member in members:
        is_head = head and head.get('name') == member['name']
        html += f'''
        <div class="member">
            <div>
                <span class="member-name">{member['name']}</span>
                {f'<span class="head-badge">👑 HEAD</span>' if is_head else ''}
                <div class="member-relation">{member['relationship']}</div>
            </div>
            <span class="badge {'badge-yes' if member['hasAadhaar'] else 'badge-no'}">
                {'✅ Aadhaar Linked' if member['hasAadhaar'] else '❌ No Aadhaar'}
            </span>
        </div>
'''
    
    html += f'''
        <div class="footer">
            Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>
'''
    return html

def format_as_csv(data):
    """Format response as CSV"""
    csv = "Member Name,Relationship,Member ID,Aadhaar Linked\n"
    for member in data['data'].get('familyMembers', []):
        csv += f'"{member["name"]}","{member["relationship"]}","{member["memberId"]}","{"Yes" if member["hasAadhaar"] else "No"}"\n'
    return csv

# For Vercel
app = app

# For local development
if __name__ == '__main__':
    app.run(debug=True, port=5000)
