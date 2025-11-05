"""
PersonaManager - Manages the lifecycle of dynamically generated personas

Handles:
- On-demand persona generation
- Memory and file-based caching
- Saving generated personas for reuse
- Promotion of effective personas to static archive
- Fallback to archived personas when generation fails
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Optional, List, Any
from framework.persona import Persona
from framework.generators import generate_personas_for_context


class PersonaManager:
    """
    Manages dynamic persona generation, caching, and persistence.

    Architecture:
    - Memory cache: Active personas for current session
    - File cache: Generated personas saved to dynamic_personas/ for reuse
    - Archive: Proven personas in personas_archive/ for fallback
    """

    def __init__(
        self,
        cache_dir: str = "dynamic_personas",
        archive_dir: str = "personas_archive",
        model_name: str = "gpt-4o-mini"
    ):
        """
        Initialize the PersonaManager.

        Args:
            cache_dir: Directory for dynamically generated persona files
            archive_dir: Directory for static/archived personas (fallback)
            model_name: LLM model to use for generation
        """
        self.cache_dir = Path(cache_dir)
        self.archive_dir = Path(archive_dir)
        self.model_name = model_name

        # Memory cache: persona_key → Persona instance
        self.memory_cache: Dict[str, Persona] = {}

        # Track generated personas per session
        self.generated_personas: List[str] = []

        # Ensure directories exist
        self.cache_dir.mkdir(exist_ok=True, parents=True)

        print(f"[PersonaManager] Initialized")
        print(f"  Cache: {self.cache_dir}")
        print(f"  Archive: {self.archive_dir}")

    def request_personas_for_phase(
        self,
        inspiration: str,
        phase_info: Dict[str, Any],
        count: int = 4
    ) -> Dict[str, Persona]:
        """
        Request personas for a specific phase.

        This is the main entry point called by the facilitator.

        Args:
            inspiration: Problem domain context
            phase_info: Current phase details
            count: Number of personas needed

        Returns:
            Dict mapping persona keys to Persona instances
        """
        print(f"\n[PersonaManager] Requesting {count} personas for phase '{phase_info.get('phase_id')}'")

        # Generate cache key based on domain and phase
        domain = self._extract_domain(inspiration)
        phase_id = phase_info.get("phase_id", "unknown")
        cache_key = f"{domain}_{phase_id}"

        # Check if we've already cached personas for this domain/phase
        cached_personas = self._load_from_file_cache(cache_key, count)
        if cached_personas:
            print(f"[PersonaManager] Using {len(cached_personas)} cached personas from file")
            return cached_personas

        # Generate new personas
        print(f"[PersonaManager] Generating new personas for domain: {domain}")
        persona_defs = generate_personas_for_context(
            inspiration=inspiration,
            phase_info=phase_info,
            existing_personas=self.generated_personas,
            count=count,
            model_name=self.model_name
        )

        if not persona_defs:
            print("[!] Persona generation failed, falling back to archive")
            return self._fallback_to_archive(count)

        # Convert to Persona instances
        personas = {}
        for persona_def in persona_defs:
            persona = Persona(persona_def, model_name=self.model_name)
            persona_key = self._create_persona_key(persona.name)

            personas[persona_key] = persona
            self.memory_cache[persona_key] = persona
            self.generated_personas.append(persona.name)

            # Save to file cache
            self._save_persona_to_cache(persona, domain, phase_id)

        print(f"[PersonaManager] Generated and cached {len(personas)} new personas")
        return personas

    def get_persona(self, persona_key: str) -> Optional[Persona]:
        """
        Retrieve a persona by key from memory cache.

        Args:
            persona_key: Normalized persona key

        Returns:
            Persona instance or None if not found
        """
        return self.memory_cache.get(persona_key)

    def _extract_domain(self, inspiration: str) -> str:
        """
        Extract a domain identifier from the inspiration text.

        Args:
            inspiration: User's problem domain text

        Returns:
            Normalized domain string (e.g., "healthcare_technology")
        """
        # Look for "Domain: <text>" pattern
        if "Domain:" in inspiration:
            domain_line = inspiration.split("Domain:")[1].split("\n")[0].strip()
        else:
            # Use first line as domain
            domain_line = inspiration.split("\n")[0].strip()

        # Normalize to lowercase with underscores
        domain = (domain_line.lower()
                 .replace(" ", "_")
                 .replace("-", "_")
                 .replace(",", "")
                 .replace(":", ""))

        # Clean up multiple underscores
        while "__" in domain:
            domain = domain.replace("__", "_")

        return domain[:50]  # Limit length

    def _create_persona_key(self, persona_name: str) -> str:
        """
        Create a normalized key from persona name.

        Args:
            persona_name: Full persona name (e.g., "Medical Device Engineer — Product Lead")

        Returns:
            Normalized key (e.g., "medical_device_engineer_product_lead")
        """
        key = (persona_name.lower()
              .replace("—", "_")
              .replace("–", "_")
              .replace("-", "_")
              .replace(" ", "_")
              .replace("/", "_"))

        # Clean up multiple underscores
        while "__" in key:
            key = key.replace("__", "_")

        return key.strip("_")

    def _load_from_file_cache(
        self,
        cache_key: str,
        count: int
    ) -> Optional[Dict[str, Persona]]:
        """
        Load personas from file cache for a given domain/phase.

        Args:
            cache_key: Domain + phase identifier
            count: Number of personas needed

        Returns:
            Dict of personas or None if not enough cached
        """
        # Create domain-specific subdirectory
        domain = cache_key.split("_")[0] if "_" in cache_key else cache_key
        domain_dir = self.cache_dir / domain

        if not domain_dir.exists():
            return None

        # Load all persona files in this domain
        persona_files = list(domain_dir.glob("*.json"))
        if len(persona_files) < count:
            return None  # Not enough cached personas

        personas = {}
        for persona_file in persona_files[:count]:
            try:
                with open(persona_file, 'r', encoding='utf-8') as f:
                    persona_def = json.load(f)

                persona = Persona(persona_def, model_name=self.model_name)
                persona_key = self._create_persona_key(persona.name)

                personas[persona_key] = persona
                self.memory_cache[persona_key] = persona

            except Exception as e:
                print(f"[!] Failed to load cached persona {persona_file.name}: {e}")
                continue

        return personas if len(personas) >= count else None

    def _save_persona_to_cache(
        self,
        persona: Persona,
        domain: str,
        phase_id: str
    ) -> None:
        """
        Save a persona to file cache.

        Args:
            persona: Persona instance to save
            domain: Domain identifier
            phase_id: Phase identifier
        """
        # Create domain-specific subdirectory
        domain_dir = self.cache_dir / domain
        domain_dir.mkdir(exist_ok=True, parents=True)

        # Create filename from persona name
        persona_key = self._create_persona_key(persona.name)
        filename = f"{persona_key}.json"
        filepath = domain_dir / filename

        # Create persona definition dict
        persona_def = {
            "Name": persona.name,
            "Archetype": persona.archetype,
            "Purpose": persona.purpose,
            "Deliverables": persona.deliverables,
            "Strengths": persona.strengths,
            "Watch-out": persona.watchouts,
            "Conversation_Style": persona.conversation_style,
            "_metadata": {
                "domain": domain,
                "phase_generated": phase_id,
                "model": self.model_name
            }
        }

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(persona_def, f, indent=2, ensure_ascii=False)
            print(f"[PersonaManager] Saved persona to cache: {filepath.name}")
        except Exception as e:
            print(f"[!] Failed to save persona to cache: {e}")

    def _fallback_to_archive(self, count: int) -> Dict[str, Persona]:
        """
        Load personas from static archive as fallback.

        Args:
            count: Number of personas needed

        Returns:
            Dict of archived personas
        """
        print(f"[PersonaManager] Loading {count} personas from archive as fallback")

        if not self.archive_dir.exists():
            print(f"[!] Archive directory not found: {self.archive_dir}")
            return {}

        persona_files = list(self.archive_dir.glob("*.json"))
        if not persona_files:
            print("[!] No archived personas found")
            return {}

        personas = {}
        for persona_file in persona_files[:count]:
            try:
                persona = Persona.from_file(str(persona_file), model_name=self.model_name)
                persona_key = self._create_persona_key(persona.name)
                personas[persona_key] = persona
                print(f"[PersonaManager] Loaded archived persona: {persona.name}")
            except Exception as e:
                print(f"[!] Failed to load archived persona {persona_file.name}: {e}")
                continue

        return personas

    def promote_to_archive(
        self,
        persona_key: str,
        reason: str = "Effective performance"
    ) -> bool:
        """
        Promote a dynamically generated persona to the static archive.

        Use this for personas that performed exceptionally well and should
        be preserved for future use across domains.

        Args:
            persona_key: Key of persona to promote
            reason: Why this persona is being promoted

        Returns:
            True if promotion successful
        """
        persona = self.memory_cache.get(persona_key)
        if not persona:
            print(f"[!] Cannot promote persona '{persona_key}' - not found in memory")
            return False

        self.archive_dir.mkdir(exist_ok=True, parents=True)

        # Save to archive with metadata
        filename = f"{persona_key}.json"
        filepath = self.archive_dir / filename

        persona_def = {
            "Name": persona.name,
            "Archetype": persona.archetype,
            "Purpose": persona.purpose,
            "Deliverables": persona.deliverables,
            "Strengths": persona.strengths,
            "Watch-out": persona.watchouts,
            "Conversation_Style": persona.conversation_style,
            "_archive_metadata": {
                "promoted_reason": reason,
                "original_model": self.model_name
            }
        }

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(persona_def, f, indent=2, ensure_ascii=False)
            print(f"[PersonaManager] ✓ Promoted persona to archive: {persona.name}")
            print(f"  Reason: {reason}")
            return True
        except Exception as e:
            print(f"[!] Failed to promote persona: {e}")
            return False

    def clear_memory_cache(self) -> None:
        """Clear the in-memory persona cache."""
        self.memory_cache.clear()
        self.generated_personas.clear()
        print("[PersonaManager] Memory cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about cached personas.

        Returns:
            Dict with cache statistics
        """
        file_count = len(list(self.cache_dir.rglob("*.json")))
        archive_count = len(list(self.archive_dir.glob("*.json"))) if self.archive_dir.exists() else 0

        return {
            "memory_cache_size": len(self.memory_cache),
            "file_cache_personas": file_count,
            "archive_personas": archive_count,
            "generated_this_session": len(self.generated_personas)
        }
