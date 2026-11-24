const baseUrl = 'https://mypublicbucket0101.obs.cn-north-4.myhuaweicloud.com/swipper/';
const nameTxtUrl = 'https://mypublicbucket0101.obs.cn-north-4.myhuaweicloud.com/swipper/name.txt';

const defaultImages = [
  baseUrl + '1.jpg',
  baseUrl + '2.jpg',
  baseUrl + '3.jpg',
  baseUrl + '4.jpg',
  baseUrl + '5.jpg',
  baseUrl + '6.jpg',
];

let images = [...defaultImages];

export function genSwiperImageList() {
  return images;
}

export function fetchSwiperImages(callback) {
  let hasCallback = false;
  const safeCallback = (data) => {
    if (!hasCallback) {
      hasCallback = true;
      callback && callback(data);
    }
  };

  setTimeout(() => {
    safeCallback(images);
  }, 5000);

  wx.request({
    url: nameTxtUrl,
    timeout: 3000,
    success: (res) => {
      if (res.statusCode === 200 && res.data) {
        const fileNames = res.data.trim().split('\n').filter(name => name.trim());
        if (fileNames.length > 0) {
          images = fileNames.map(name => baseUrl + encodeURIComponent(name.trim()));
        }
      }
      safeCallback(images);
    },
    fail: () => {
      safeCallback(images);
    },
  });
}
