# Prerequisites

1. Create a Cloudflare Account API token with 3 permissions: `Access: Identity Providers`, `Cloudflare Pages`, `Access: Apps and Policies`. For each select Account in the first column and Edit in the third column. Remember to store your token before exiting as it won't be visible afterwards.
2. Integrate github with Cloudflare. Go to a Cloudflare website -> Build -> Compute -> Workers & Pages -> Create application -> wait for few seconds and click Connect GitHub -> after selecting repos click Install & Authorize and you can close the website. The rest will be done from terraform. https://developers.cloudflare.com/pages/get-started/git-integration/
3. Enable zero trust on Cloudflare. Go to a Cloudflare website -> Protect & Connect -> Zero Trust -> Get started -> pick a name -> Zero Trust Free Select plan -> fillin a card details
4. Create a client id and a client secret for using Google as an identity provider. Follow this tutorial until step 9: https://developers.cloudflare.com/cloudflare-one/integrations/identity-providers/google/
5. Create a tfvars file with all the needed values:
