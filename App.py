import os
from flask import Flask, jsonify, request
from supabase import Client, create_client

app = Flask(__name__)

# Environment variable safety check
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
  raise ValueError("Missing Supabase environment variables in .env file!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


@app.route("/", methods=["GET"])
def home():
  return (
      jsonify({
          "status": "online",
          "service": "MatrixDesk Multi-Tenant API Engine",
      }),
      200,
  )


@app.route("/api/register", methods=["POST"])
def register_vendor():
  data = request.get_json() or {}

  business_name = data.get("business_name")
  owner_full_name = data.get("owner_full_name")
  email = data.get("email")
  password = data.get("password")
  phone = data.get("phone")

  # Validate required fields
  if not all([business_name, owner_full_name, email, password]):
    return jsonify({"error": "Missing required fields for registration."}), 400

  user_id = None

  try:
    # 1. Create user credential in Supabase Auth
    auth_response = supabase.auth.admin.create_user({
        "email": email,
        "password": password,
        "email_confirm": True,
    })

    user_id = (
        auth_response.user.id
        if auth_response and auth_response.user
        else None
    )
    if not user_id:
      return jsonify({"error": "Failed to create authentication record."}), 500

    # 2. Insert record into public.tenants table (including owner_user_id reference)
    tenant_res = (
        supabase.table("tenants")
        .insert({
            "business_name": business_name,
            "owner_full_name": owner_full_name,
            "email": email,
            "phone": phone,
            "owner_user_id": user_id,  # Linked directly per reviewer specs
            "status": "locked",
        })
        .execute()
    )

    if not tenant_res.data:
      raise Exception("Failed to insert tenant record.")

    tenant_id = tenant_res.data[0]["id"]

    # 3. Link the user to the tenant in public.profiles table
    profile_res = (
        supabase.table("profiles")
        .insert({
            "id": user_id,
            "tenant_id": tenant_id,
            "full_name": owner_full_name,
            "email": email,
            "role": "vendor_admin",
        })
        .execute()
    )

    if not profile_res.data:
      raise Exception("Failed to link profile record.")

    return (
        jsonify({
            "message": (
                "Registration successful! Account created and pending review."
            ),
            "tenant_id": tenant_id,
            "email": email,
        }),
        201,
    )

  except Exception as e:
    # Atomic Rollback: Clean up auth user if any table insert fails
    if user_id:
      try:
        supabase.auth.admin.delete_user(user_id)
      except Exception as cleanup_error:
        print(f"Failed to cleanup orphaned auth user: {cleanup_error}")

    # Security Shield: Log real error internally, return safe message externally
    print(f"Registration Error: {str(e)}")
    return jsonify({"error": "Registration failed, please try again."}), 500


if __name__ == "__main__":
  app.run(debug=False, port=5000)
