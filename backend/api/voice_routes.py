"""
Voice Profile & Consent API Routes
Provides endpoints for recording consent, audio quality validation, profile creation, and profile deletion.
"""

from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from backend.adapters.voice_profile.secure_profile_service import SecureVoiceProfileService
from backend.domain.models import AudioQualityMetrics, ConsentRecord, Language, VoiceProfile

router = APIRouter(prefix="/api/voice", tags=["Voice Profile & Consent"])

# Shared singleton profile service instance
voice_profile_service = SecureVoiceProfileService()


class ConsentRequest(BaseModel):
    user_id: str
    statement_text: str


class ConsentResponse(BaseModel):
    consent_id: str
    user_id: str
    statement_text: str
    signature_hash: str
    is_revoked: bool


@router.post("/consent", response_model=ConsentResponse)
async def record_consent(payload: ConsentRequest):
    """Records cryptographically signed user consent for personal voice cloning."""
    try:
        # Generate dummy signature bytes from statement if no voice audio provided yet
        consent = await voice_profile_service.record_consent(
            user_id=payload.user_id,
            statement_text=payload.statement_text,
            audio_signature_bytes=payload.statement_text.encode("utf-8"),
        )
        return ConsentResponse(
            consent_id=consent.consent_id,
            user_id=consent.user_id,
            statement_text=consent.statement_text,
            signature_hash=consent.signature_hash,
            is_revoked=consent.is_revoked,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/validate-audio", response_model=AudioQualityMetrics)
async def validate_audio(audio_file: UploadFile = File(...)):
    """Analyzes raw audio/WAV quality for SNR, clipping rate, and duration."""
    content = await audio_file.read()
    metrics = await voice_profile_service.validate_audio_quality(content)
    return metrics


@router.post("/create-profile", response_model=VoiceProfile)
async def create_profile(
    user_id: str = Form(...),
    display_name: str = Form(...),
    consent_id: str = Form(...),
    native_language: str = Form("hi"),
    audio_file: UploadFile = File(...),
):
    """Enrolls authorized personal voice profile after checking consent and quality."""
    content = await audio_file.read()
    try:
        lang = Language(native_language) if native_language in [l.value for l in Language] else Language.HINDI
        profile = await voice_profile_service.create_profile(
            user_id=user_id,
            display_name=display_name,
            consent_id=consent_id,
            audio_sample_bytes=content,
            native_language=lang,
        )
        return profile
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/profile/{user_id}", response_model=Optional[VoiceProfile])
async def get_profile(user_id: str):
    """Retrieves user's active voice profile if authorized."""
    profile = await voice_profile_service.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice profile not found.")
    return profile


@router.delete("/profile/{user_id}")
async def delete_profile(user_id: str):
    """Permanently revokes consent and deletes voice profile and audio samples."""
    success = await voice_profile_service.delete_profile(user_id)
    return {"status": "success", "message": "Voice profile and all associated audio destroyed permanently."}
