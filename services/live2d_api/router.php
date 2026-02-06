<?php
// --- CORS Headers (MUST be set before any output) ---
// Set the CORS header to allow access from any origin.
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: GET, POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type");

// Handle pre-flight OPTIONS requests separately.
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    // For pre-flight, we only need to send the headers and stop.
    exit(0);
}
// ----------------------------------------------------

// Determine the full path to the requested resource.
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$filepath = __DIR__ . $path;

// 1. Security Check: Prevent serving .php files directly as static assets.
if (strtolower(substr($filepath, -4)) === '.php') {
    // If it's a PHP script, let the server execute it normally (return false).
    return false; 
}

// 2. File Check: If the file exists and is not a directory.
if (is_file($filepath)) {
    // We must manually set the Content-Type header before reading the file,
    // otherwise the browser might interpret the file incorrectly.
    $mime_type = mime_content_type($filepath);
    if ($mime_type !== false) {
        header("Content-Type: " . $mime_type);
    }
    
    // CRITICAL FIX: Manually read and output the file contents.
    // This prevents the PHP server from handling it as a raw static asset
    // (which would strip the headers) and ensures our CORS header is included.
    readfile($filepath);
    
    // Stop script execution successfully after sending the file.
    return true; 
}

// 3. Fallback: If the file was not found (404), return false 
//    to let the server handle the 404 response or look for index.php/index.html.
return false;
?>
