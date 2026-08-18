export function roleForCharacter(characterId, characterRoles = {}) {
  return characterRoles[characterId] ?? (characterId === 'Alice' ? 'guest' : 'staff');
}
