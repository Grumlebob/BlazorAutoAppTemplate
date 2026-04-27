namespace BlazorAutoApp.Features.Movies;

// Movies-specific validation filter using DataAnnotations on request DTOs
public class MoviesValidateFilter<T> : IEndpointFilter where T : class
{
    public async ValueTask<object?> InvokeAsync(EndpointFilterInvocationContext context, EndpointFilterDelegate next)
    {
        var arg = context.Arguments.OfType<T>().FirstOrDefault();
        if (arg is null)
        {
            return await next(context);
        }

        var validationResults = new List<ValidationResult>();
        var vc = new ValidationContext(arg, context.HttpContext.RequestServices, null);
        bool isValid = Validator.TryValidateObject(arg, vc, validationResults, validateAllProperties: true);

        if (!isValid)
        {
            var errors = new Dictionary<string, string[]>(System.StringComparer.OrdinalIgnoreCase);
            foreach (var result in validationResults)
            {
                var members = result.MemberNames?.Any() == true ? result.MemberNames : [string.Empty];
                foreach (var member in members)
                {
                    if (!errors.TryGetValue(member, out var list))
                    {
                        errors[member] = [result.ErrorMessage ?? "Validation error"];
                    }
                    else
                    {
                        errors[member] = [.. list, .. new[] { result.ErrorMessage ?? "Validation error" }];
                    }
                }
            }

            return Results.ValidationProblem(errors);
        }

        return await next(context);
    }
}

