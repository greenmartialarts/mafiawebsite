from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from .models import Room, RoleAssignment, Player, BugReport
from .forms import RoomCreationForm, JoinRoomForm, PlayerForm, CustomUserCreationForm, BugReportForm
import random
import string
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
from django.utils import timezone
from datetime import timedelta
from django.db.models import F
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.urls import reverse
from .utils import get_device_type

def home(request):
    return render(request, 'myapp/home.html')

@login_required
def create_room(request):
    if request.method == 'POST':
        form = RoomCreationForm(request.POST)
        if form.is_valid():
            room = form.save(commit=False)
            room.host = request.user
            room.room_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            room.save()
            
            # Ensure the host has a session key
            if not request.session.session_key:
                request.session.create()
                
            # Create a Player object for the host
            host_player = Player.objects.create(
                name=request.user.username,
                session_key=request.session.session_key,
                device_order=0
            )
            room.temp_players.add(host_player)
            
            return redirect('waiting_room', room_code=room.room_code)
    else:
        form = RoomCreationForm()
    return render(request, 'myapp/create_room.html', {'form': form})

def join_room(request):
    if request.method == 'POST':
        room_form = JoinRoomForm(request.POST)
        player_count = int(request.POST.get('player_count', 1))
        
        if room_form.is_valid():
            room_code = room_form.cleaned_data['room_code']
            password = room_form.cleaned_data['password']
            
            try:
                room = Room.objects.get(room_code=room_code)
                
                # Check if user is banned
                if request.user.is_authenticated and room.banned_users.filter(id=request.user.id).exists():
                    messages.error(request, 'You are banned from this room')
                    return redirect('home')
                
                # Check password if room is password protected
                if room.is_password_protected() and room.password != password:
                    messages.error(request, 'Invalid password')
                    return render(request, 'myapp/join_room.html', {
                        'room_form': room_form
                    })
                
                # Create players for this device
                if not request.session.session_key:
                    request.session.create()
                
                for i in range(player_count):
                    player_name = request.POST.get(f'player_name_{i}')
                    if player_name:
                        player = Player.objects.create(
                            name=player_name,
                            session_key=request.session.session_key,
                            device_order=i
                        )
                        room.temp_players.add(player)
                
                return redirect('waiting_room', room_code=room_code)
            except Room.DoesNotExist:
                messages.error(request, 'Invalid room code')
    else:
        room_form = JoinRoomForm()
    
    return render(request, 'myapp/join_room.html', {
        'room_form': room_form
    })

def _get_player_list_html(room):
    players = list(room.players.all()) + list(room.temp_players.all())
    html = ''
    for player in players:
        if hasattr(player, 'username'):
            name = player.username
        else:
            name = player.name
        host_badge = '<span class="badge bg-primary">Host</span>' if player == room.host else ''
        html += f'<li class="list-group-item">{name} {host_badge}</li>'
    return html

def waiting_room(request, room_code):
    room = get_object_or_404(Room, room_code=room_code)
    is_host = request.user.is_authenticated and request.user == room.host
    device_type = get_device_type(request)
    
    # Get all players (both authenticated and temporary)
    players = list(room.players.all()) + list(room.temp_players.all())
    
    context = {
        'room': room,
        'is_host': is_host,
        'players': players,
        'device_type': device_type,
    }
    return render(request, 'myapp/waiting_room.html', context)

@login_required
def assign_roles(request, room_code):
    room = get_object_or_404(Room, room_code=room_code)
    if request.user != room.host:
        messages.error(request, 'Only the host can assign roles')
        return redirect('waiting_room', room_code=room_code)

    # Get all players (both authenticated and temporary)
    all_players = list(room.players.all()) + list(room.temp_players.all())
    roles = (['MAFIA'] * room.mafia_count +
             ['DOCTOR'] * room.doctor_count +
             ['COP'] * room.cop_count)
    
    # Fill remaining with villagers
    roles += ['VILLAGER'] * (len(all_players) - len(roles))
    random.shuffle(roles)

    # Clear existing assignments
    RoleAssignment.objects.filter(room=room).delete()
    
    # Assign roles to all players
    for player, role in zip(all_players, roles):
        RoleAssignment.objects.create(
            user=player if isinstance(player, User) else None,
            temp_player=player if isinstance(player, Player) else None,
            room=room,
            role=role
        )
    
    room.special_role_assigned = True
    room.save()
    
    return redirect('role_display', room_code=room_code)

def role_display(request, room_code):
    room = get_object_or_404(Room, room_code=room_code)
    show_role = request.GET.get('show_role', False)
    
    # Get all players for this device
    session_key = request.session.session_key
    device_players = Player.objects.filter(
        session_key=session_key,
        joined_rooms=room
    ).order_by('device_order')
    
    # Find first player who hasn't viewed their role
    current_player = device_players.filter(has_viewed_role=False).first()
    
    if current_player:
        role_assignment = get_object_or_404(
            RoleAssignment,
            temp_player=current_player,
            room=room
        )
    else:
        role_assignment = None
        show_role = False
    
    return render(request, 'myapp/role_display.html', {
        'room': room,
        'current_player': current_player,
        'role_assignment': role_assignment,
        'show_role': show_role
    })

def leave_room(request, room_code):
    room = get_object_or_404(Room, room_code=room_code)
    
    if request.user.is_authenticated:
        if request.user == room.host:
            room.delete()
        else:
            room.players.remove(request.user)
    else:
        # Remove temporary player
        temp_player = room.temp_players.filter(session_key=request.session.session_key).first()
        if temp_player:
            room.temp_players.remove(temp_player)
            temp_player.delete()
    
    return redirect('home')

def get_player_list(request, room_code):
    room = get_object_or_404(Room, room_code=room_code)
    players = list(room.players.all()) + list(room.temp_players.all())
    is_host = request.user.is_authenticated and request.user == room.host
    
    # Add player count badge HTML
    player_count_html = f'''
        <h3>
            <i class="fas fa-users me-2"></i>Players
            <span class="badge bg-primary">{len(players)}</span>
        </h3>
    '''
    
    player_list_html = ''
    for player in players:
        if hasattr(player, 'username'):
            name = player.username
            # Only show kick/ban for authenticated users
            if is_host and player != room.host:
                host_badge = f'''
                    <div class="btn-group">
                        <a href="{reverse("kick_player", kwargs={"room_code": room.room_code, "player_id": player.id})}"
                           class="btn btn-sm btn-warning"
                           onclick="return confirm('Are you sure you want to kick {player.username}?')">
                            <i class="fas fa-user-times me-1"></i>Kick
                        </a>
                        <a href="{reverse('ban_player', kwargs={'room_code': room.room_code, 'player_id': player.id})}"
                           class="btn btn-sm btn-danger"
                           onclick="return confirm('Are you sure you want to ban {player.username}? They will not be able to rejoin this room.')">
                            <i class="fas fa-ban me-1"></i>Ban
                        </a>
                    </div>
                '''
            elif player == room.host:
                host_badge = '<span class="badge bg-primary"><i class="fas fa-crown me-1"></i>Host</span>'
            else:
                host_badge = ''
        else:
            name = player.name
            host_badge = ''
            
        player_list_html += f'''
            <li class="list-group-item d-flex justify-content-between align-items-center">
                <span><i class="fas fa-user me-2"></i>{name}</span>
                {host_badge}
            </li>
        '''
    
    # Check if roles have been assigned
    roles_assigned = room.special_role_assigned
    
    return JsonResponse({
        'player_list_html': player_list_html,
        'player_count_html': player_count_html,
        'roles_assigned': roles_assigned,
        'total_players': len(players)
    })

def mark_ready(request, room_code):
    room = get_object_or_404(Room, room_code=room_code)
    
    # Increment the ready count
    room.players_ready = F('players_ready') + 1
    room.save()
    
    # Refresh from database to get actual count
    room.refresh_from_db()
    
    # If all players are ready, set the timestamp
    total_players = room.players.count() + room.temp_players.count()
    if room.players_ready >= total_players and not room.all_ready_at:
        room.all_ready_at = timezone.now()
        room.save()
    
    return redirect('home')

def check_room_status(request, room_code):
    room = get_object_or_404(Room, room_code=room_code)
    room_deleted = False
    
    if room.all_ready_at:
        # Check if 10 minutes have passed since all players were ready
        if timezone.now() >= room.all_ready_at + timedelta(minutes=10):
            room.delete()
            room_deleted = True
    
    return JsonResponse({
        'room_deleted': room_deleted
    })

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Log the user in after registration
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'myapp/register.html', {'form': form})

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep user logged in
            messages.success(request, 'Your password was successfully updated!')
            return redirect('home')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'myapp/change_password.html', {'form': form})

@login_required
def delete_account(request):
    if request.method == 'POST':
        user = request.user
        # Check if user is not an admin
        if not user.is_superuser and not user.is_staff:
            user.delete()
            messages.success(request, 'Your account has been successfully deleted.')
            return redirect('home')
        else:
            messages.error(request, 'Admin accounts cannot be deleted.')
    return render(request, 'myapp/delete_account.html')

def report_bug(request):
    if request.method == 'POST':
        form = BugReportForm(request.POST)
        if form.is_valid():
            bug_report = form.save(commit=False)
            if request.user.is_authenticated:
                bug_report.reporter = request.user
            bug_report.save()
            messages.success(request, 'Bug report submitted successfully!')
            return redirect('bug_list')
    else:
        form = BugReportForm()
    return render(request, 'myapp/report_bug.html', {'form': form})

def bug_list(request):
    if request.user.is_staff:
        # Staff can see all bugs
        bugs = BugReport.objects.all().order_by('-created_at')
        can_edit = True
    elif request.user.is_authenticated:
        # Users can see their own reported bugs
        bugs = BugReport.objects.filter(reporter=request.user).order_by('-created_at')
        can_edit = True
    else:
        # Guest users can see all bugs but can't edit
        bugs = BugReport.objects.all().order_by('-created_at')
        can_edit = False
    
    return render(request, 'myapp/bug_list.html', {
        'bugs': bugs,
        'can_edit': can_edit
    })

@login_required
def bug_detail(request, bug_id):
    bug = get_object_or_404(BugReport, id=bug_id)
    if not request.user.is_staff and bug.reporter != request.user:
        messages.error(request, 'You do not have permission to view this bug report.')
        return redirect('bug_list')
    return render(request, 'myapp/bug_detail.html', {'bug': bug})

@login_required
def kick_player(request, room_code, player_id):
    room = get_object_or_404(Room, room_code=room_code)
    if request.user != room.host:
        messages.error(request, 'Only the host can kick players')
        return redirect('waiting_room', room_code=room_code)
    
    try:
        player = User.objects.get(id=player_id)
        if player == room.host:
            messages.error(request, 'Cannot kick the host')
            return redirect('waiting_room', room_code=room_code)
        
        room.players.remove(player)
        messages.success(request, f'{player.username} has been kicked')
    except User.DoesNotExist:
        messages.error(request, 'Player not found')
    
    return redirect('waiting_room', room_code=room_code)

@login_required
def ban_player(request, room_code, player_id):
    room = get_object_or_404(Room, room_code=room_code)
    if request.user != room.host:
        messages.error(request, 'Only the host can ban players')
        return redirect('waiting_room', room_code=room_code)
    
    try:
        player = User.objects.get(id=player_id)
        if player == room.host:
            messages.error(request, 'Cannot ban the host')
            return redirect('waiting_room', room_code=room_code)
        
        room.players.remove(player)
        room.banned_users.add(player)
        messages.success(request, f'{player.username} has been banned')
    except User.DoesNotExist:
        messages.error(request, 'Player not found')
    
    return redirect('waiting_room', room_code=room_code)

def mark_role_viewed(request, room_code):
    if request.method == 'POST':
        room = get_object_or_404(Room, room_code=room_code)
        session_key = request.session.session_key
        
        # Get current player
        current_player = Player.objects.filter(
            session_key=session_key,
            joined_rooms=room,
            has_viewed_role=False
        ).order_by('device_order').first()
        
        if current_player:
            current_player.has_viewed_role = True
            current_player.save()
        
        return JsonResponse({'redirect': True})
    
    return JsonResponse({'redirect': False})
