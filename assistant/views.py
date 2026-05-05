from django.contrib.auth import logout
from .models import UserProfile, UserMemory, ChatHistory, CustomUser
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .rag_engine import rag_engine
import json
import re
import random
import string
import bcrypt
from django.core.mail import send_mail
from django.contrib import messages
from django.conf import settings
from functools import wraps

def session_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if "user_id" not in request.session and not request.user.is_authenticated:
            return redirect("assistant:login")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

import uuid

def index(request):
    from django.contrib.auth.models import User
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import Max
    
    sessions_list = []
    display_name = "Guest"
    user_id = request.session.get("user_id")
    current_session_id = request.GET.get('session')

    # Bridge between allauth and custom session auth
    if not user_id and request.user.is_authenticated:
        custom_user, created = CustomUser.objects.get_or_create(
            email=request.user.email,
            defaults={
                'name': request.user.get_full_name() or request.user.email.split('@')[0],
                'password': 'social_auth_user' # Dummy password for social users
            }
        )
        request.session["user_id"] = custom_user.id
        user_id = custom_user.id

    full_history = []
    full_history_json = "[]"
    if user_id:
        try:
            custom_user = CustomUser.objects.get(id=user_id)
            display_name = custom_user.name or custom_user.email
            django_user, _ = User.objects.get_or_create(username=custom_user.email, email=custom_user.email)
            
            # Get all distinct sessions for this user, grouping only by session_id
            # We use annotate to get the latest timestamp and then we'll get the title for each unique session_id
            session_ids = ChatHistory.objects.filter(user=django_user).values('session_id').annotate(latest=Max('timestamp')).order_by('-latest')
            
            for sess_data in session_ids:
                sid = sess_data['session_id']
                if sid:
                    # Get the title from the first message in this session
                    first_msg = ChatHistory.objects.filter(user=django_user, session_id=sid).first()
                    sessions_list.append({
                        'id': sid,
                        'title': first_msg.session_title if first_msg else "New Chat"
                    })

            # Get full chat history for the selected session
            if current_session_id:
                history_objs = ChatHistory.objects.filter(user=django_user, session_id=current_session_id).order_by('timestamp')
                for msg in history_objs:
                    full_history.append({
                        'role': 'user' if msg.role == 'user' else 'ai',
                        'content': msg.content
                    })
                full_history_json = json.dumps(full_history)
                    
        except Exception as e:
            print(f"Error loading history: {e}")
    
    return render(request, 'assistant/index.html', {
        'sessions': sessions_list, 
        'full_history_json': full_history_json,
        'current_session_id': current_session_id,
        'display_name': display_name,
        'is_logged_in': user_id is not None
    })

@csrf_exempt
def ask(request):
    if request.method != 'POST':
        return JsonResponse({"error": "POST method required"}, status=405)

    try:
        data = json.loads(request.body)
        question = data.get("question", "")
        session_id = data.get("session_id")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if not question:
        return JsonResponse({"error": "No question provided"}, status=400)

    user_id = request.session.get("user_id")
    user_memory_context = "I don't know the user's name yet."
    chat_history_str = ""
    django_user = None

    if user_id:
        from django.contrib.auth.models import User
        try:
            custom_user = CustomUser.objects.get(id=user_id)
            django_user, _ = User.objects.get_or_create(username=custom_user.email, email=custom_user.email)

            if not session_id:
                session_id = str(uuid.uuid4())

            # 1. User Memory Logic
            name_match = re.search(r"my name is ([\w\s]+)", question, re.IGNORECASE)
            if name_match:
                name = name_match.group(1).strip()
                UserMemory.objects.update_or_create(
                    user=django_user, 
                    key='name', 
                    defaults={'value': name}
                )

            # 2. Get Contextual Data
            user_name_obj = UserMemory.objects.filter(user=django_user, key='name').first()
            user_name = user_name_obj.value if user_name_obj else None
            user_memory_context = f"User's name is {user_name}." if user_name else "I don't know the user's name yet."
            
            # Context only from the CURRENT session
            history_objs = ChatHistory.objects.filter(user=django_user, session_id=session_id).order_by('-timestamp')[:10]
            chat_history_str = "\n".join([f"{msg.role}: {msg.content}" for msg in reversed(history_objs)])
        except CustomUser.DoesNotExist:
            user_id = None

    # 3. Get Answer from RAG Engine
    try:
        answer = rag_engine.get_answer(question, user_memory_context, chat_history_str)
    except Exception as e:
        print(f"Error in RAG Engine: {str(e)}")
        return JsonResponse({"error": str(e), "answer": "I encountered an internal error."}, status=500)

    # 4. Log to DB if logged in
    if django_user:
        # If it's a new session, set the title based on the first question
        existing_msg = ChatHistory.objects.filter(user=django_user, session_id=session_id).first()
        if existing_msg:
            session_title = existing_msg.session_title
        else:
            session_title = question[:50] + ("..." if len(question) > 50 else "")
        
        ChatHistory.objects.create(user=django_user, role='user', content=question, session_id=session_id, session_title=session_title)
        ChatHistory.objects.create(user=django_user, role='assistant', content=answer, session_id=session_id, session_title=session_title)
        return JsonResponse({"answer": answer, "session_id": session_id})
    else:
        # For guest users, return the answer and a redirect hint
        return JsonResponse({
            "answer": answer,
            "redirect": reverse("assistant:login")
        })

@csrf_exempt
@session_login_required
def reset(request):
    from django.contrib.auth.models import User
    custom_user = CustomUser.objects.get(id=request.session["user_id"])
    django_user = User.objects.get(username=custom_user.email)
    ChatHistory.objects.filter(user=django_user).delete()
    return JsonResponse({"message": "Memory reset successful."})

@csrf_exempt
@session_login_required
def delete_session(request):
    session_id = request.GET.get('session_id')
    if not session_id:
        return JsonResponse({"error": "No session ID provided"}, status=400)
    
    from django.contrib.auth.models import User
    custom_user = CustomUser.objects.get(id=request.session["user_id"])
    django_user = User.objects.get(username=custom_user.email)
    
    deleted_count, _ = ChatHistory.objects.filter(user=django_user, session_id=session_id).delete()
    return JsonResponse({"message": f"Session deleted successfully. {deleted_count} messages removed."})

def generate_captcha():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@csrf_exempt
def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            user = CustomUser.objects.get(email=email)
            if bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
                request.session["user_id"] = user.id
                return redirect("assistant:index")
            else:
                return render(request, "registration/login.html", {"error": "Invalid password", "captcha_code": generate_captcha()})
        except CustomUser.DoesNotExist:
            return render(request, "registration/login.html", {"error": "Invalid email", "captcha_code": generate_captcha()})

    captcha_code = generate_captcha()
    request.session["captcha_code"] = captcha_code
    return render(request, "registration/login.html", {"captcha_code": captcha_code})

@csrf_exempt
def signup_view(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if CustomUser.objects.filter(email=email).exists():
            return render(request, "registration/login.html", {
                "error": "Email already registered.",
                "show_form": "signupForm",
                "captcha_code": generate_captcha()
            })

        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        otp = str(random.randint(100000, 999999))

        request.session["signup_data"] = {
            "name": name,
            "email": email,
            "password": hashed,
            "otp": otp,
        }

        try:
            send_mail(
                subject="Your OTP Verification",
                message=f"Your OTP is {otp}",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
            )
            print(f"OTP email sent successfully to {email}")
        except Exception as e:
            print(f"FAILED TO SEND OTP EMAIL: {str(e)}")
            return render(request, "registration/login.html", {
                "error": f"Failed to send email: {e}",
                "show_form": "signupForm",
                "captcha_code": generate_captcha()
            })

        return redirect(f"{reverse('assistant:otp')}?email={email}")

    return redirect("assistant:login")

@csrf_exempt
def otp_verify(request):
    email = request.GET.get("email")
    signup_data = request.session.get("signup_data")

    if request.method == "POST":
        entered_otp = request.POST.get("otp")

        if signup_data and entered_otp == signup_data["otp"]:
            user = CustomUser.objects.create(
                name=signup_data["name"],
                email=signup_data["email"],
                password=signup_data["password"]
            )
            request.session["user_id"] = user.id
            del request.session["signup_data"]
            return redirect("assistant:index")
        else:
            return render(request, "registration/otp.html", {"email": email, "error": "Invalid OTP"})

    return render(request, "registration/otp.html", {"email": email})

@csrf_exempt
def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")
        entered_captcha = request.POST.get("captcha")
        session_captcha = request.session.get("captcha_code")

        if entered_captcha != session_captcha:
            return render(request, "registration/login.html", {"error": "Captcha does not match!", "captcha_code": generate_captcha(), "show_form": "forgotForm"})

        if new_password != confirm_password:
            return render(request, "registration/login.html", {"error": "Passwords do not match!", "captcha_code": generate_captcha(), "show_form": "forgotForm"})

        try:
            user = CustomUser.objects.get(email=email)
            otp = str(random.randint(100000, 999999))
            
            hashed_new = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            request.session["reset_data"] = {
                "email": email,
                "new_password": hashed_new,
                "otp": otp,
            }

            send_mail(
                subject="Password Reset OTP",
                message=f"Your OTP is {otp}",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
            )
            return redirect(f"{reverse('assistant:reset_otp')}?email={email}")

        except CustomUser.DoesNotExist:
            return render(request, "registration/login.html", {"error": "No account found with this email.", "captcha_code": generate_captcha(), "show_form": "forgotForm"})

    return redirect("assistant:login")

@csrf_exempt
def reset_otp_verify(request):
    email = request.GET.get("email")
    reset_data = request.session.get("reset_data")

    if request.method == "POST":
        entered_otp = request.POST.get("otp")
        
        if reset_data and entered_otp == reset_data["otp"]:
            user = CustomUser.objects.get(email=email)
            user.password = reset_data["new_password"]
            user.save()
            del request.session["reset_data"]
            messages.success(request, "Password reset successful! Please login.")
            return redirect("assistant:login")
        else:
            return render(request, "registration/otp.html", {"email": email, "error": "Invalid OTP", "is_reset": True})

    return render(request, "registration/otp.html", {"email": email, "is_reset": True})

@csrf_exempt
def resend_otp(request):
    signup_data = request.session.get("signup_data")
    reset_data = request.session.get("reset_data")
    
    if signup_data:
        otp = str(random.randint(100000, 999999))
        signup_data["otp"] = otp
        request.session["signup_data"] = signup_data
        send_mail(subject="New OTP", message=f"Code: {otp}", from_email=settings.EMAIL_HOST_USER, recipient_list=[signup_data["email"]])
        return redirect(f"{reverse('assistant:otp')}?email={signup_data['email']}")
    elif reset_data:
        otp = str(random.randint(100000, 999999))
        reset_data["otp"] = otp
        request.session["reset_data"] = reset_data
        send_mail(subject="Reset OTP", message=f"Code: {otp}", from_email=settings.EMAIL_HOST_USER, recipient_list=[reset_data["email"]])
        return redirect(f"{reverse('assistant:reset_otp')}?email={reset_data['email']}")
    return redirect("assistant:login")

def refresh_captcha(request):
    captcha_code = generate_captcha()
    request.session["captcha_code"] = captcha_code
    return JsonResponse({"captcha": captcha_code})

def logout_view(request):
    request.session.flush()
    return redirect("assistant:login")
