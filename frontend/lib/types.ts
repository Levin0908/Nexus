export interface UserPublic {
  id: string;
  email: string;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
}

export interface DocumentPublic {
  id: string;
  owner_id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  storage_path: string;
  sha256: string;
  status: "uploading" | "ready" | "failed";
  extracted_text: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentSearchHit {
  id: string;
  owner_id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  storage_path: string;
  sha256: string;
  status: "uploading" | "ready" | "failed";
  rank: number;
  created_at: string;
  updated_at: string;
}

export interface ApiError {
  detail: string;
}
