using Microsoft.AspNetCore.Identity;

namespace GrumPlates.Features.Login.Account;

// Preserve the mapped CLR identity used by the existing migration history and model snapshot.
public class ApplicationUser : IdentityUser
{
}
