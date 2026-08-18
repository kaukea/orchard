---
name: coding-dotnet
description: "Use for any .NET or C# code change: implement, edit, modify, refactor, fix, add, remove, rename, or update code, tests, or project files."
categories: [development/dotnet]
metadata:
  tags: [dotnet, csharp, native-aot, dotnet-refactor, dotnet-tests, project-files]
  share: github
---

# Dotnet Coding

Use this skill for implementation work in `.NET` repositories, especially when changing `C#` code, tests, or project files.

## Checklist

- [ ] Target framework + language version match the project (latest by default — .NET 10 / C# 14+)
- [ ] Changes stayed local to the requested feature; no incidental refactors
- [ ] No new interfaces unless a real second implementation or seam exists
- [ ] No swallowed exceptions, no speculative guards
- [ ] No comments added unless absolutely necessary
- [ ] New types live in new files
- [ ] Style matches the file being edited
- [ ] Architectural changes were confirmed by the user before applying

## Defaults

- Target `.NET 10` and `C# 14` or newer
- Always use the latest language and framework features
- Keep Native AOT compatibility in mind by default
- Follow `SOLID`, `KISS`, composition over inheritance
- Prefer composable components when they can share the same interface
- Prefer functional style where it fits naturally
- Write only enough code to fulfill the feature
- Do not add speculative guards for unlikely events
- Do not catch and swallow exceptions
- Always use self-descriptive code, do not add redundant suffixes (e.g. DTO, Service)
- Design from current requirements, not from possible future variation
- Prefer composition of concrete domain components over configuration-heavy plumbing
- Keep one consistent numeric type and one consistent scale for the same concept across the codebase

## Style
- Do not add comments unless absolutely necessary
- Follow standard naming conventions
- Match the style of the file you are editing
- Always create a new file for new types.

## Editing Rules

- Keep changes local unless broader change is required
- Do not change architecture without confirmation by the user
- Reuse existing patterns before introducing new ones
- Keep public APIs and behavior stable unless the task requires a change
- In test projects, follow the test project's existing conventions
- Keep related types close to the feature or format they belong to; do not create broad buckets for type categories
- Do not add interfaces unless there is a real second implementation or a concrete seam that needs one
- Understand the full API surface before choosing a .NET API; do not
  shoehorn one overload or one method in isolation
- Prefer the latest official .NET APIs and language constructs that fit the
  target framework instead of legacy-compatible patterns
- Avoid type- and assembly-based runtime patterns in AOT-sensitive paths
  unless the documented API specifically requires them
- Do not let inactive persistence or infrastructure paths dictate the shape of active code
- Prefer contracts that tell the truth: avoid nullable return types for operations where failure should be exceptional
- Prefer domain objects over raw primitive coordination when the code is really talking about a concrete thing, such as a document or page

## Stop

Stop when the requested change is complete and verified enough for the current task.
