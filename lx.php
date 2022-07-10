<?php
error_reporting(0);
$url = $_GET['url'];

$jx ="http://106.55.234.91:4433/?url=$url";
$headerArray = array(
        "User-Agent: Dalvik/2.1.0",
    );
    $curl = curl_init();
    curl_setopt($curl, CURLOPT_URL, $jx);
    curl_setopt($curl, CURLOPT_SSL_VERIFYPEER, FALSE);
    curl_setopt($curl, CURLOPT_SSL_VERIFYHOST, FALSE);
    curl_setopt($curl, CURLOPT_HTTPHEADER, $headerArray);
    curl_setopt($curl, CURLOPT_RETURNTRANSFER, 1);
    $output = curl_exec($curl);
    curl_close($curl);

$arr=json_decode($output,true);
$play =  $arr['data']['url'];
echo $play;
header("Content-type:application/vnd.apple.mpegurl");


?>