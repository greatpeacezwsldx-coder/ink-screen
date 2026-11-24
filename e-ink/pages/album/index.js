Page({
  data: {
    photos: []
  },
  onLoad() {
    this.loadPhotos()
  },
  loadPhotos() {
    let photos = [
      { id: '1', url: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=beautiful%20sunset%20beach&image_size=square' },
      { id: '2', url: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=colorful%20flowers%20garden&image_size=square' },
      { id: '3', url: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=city%20skyline%20night&image_size=square' },
      { id: '4', url: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=mountains%20landscape%20fog&image_size=square' },
      { id: '5', url: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=cute%20cat%20playing&image_size=square' },
      { id: '6', url: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=delicious%20food%20dinner&image_size=square' },
      { id: '7', url: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=forest%20path%20sunlight&image_size=square' },
      { id: '8', url: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=stars%20milky%20way%20night&image_size=square' },
      { id: '9', url: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=waterfall%20nature%20green&image_size=square' }
    ]
    this.setData({ photos })
  },
  previewPhoto(e) {
    let index = e.currentTarget.dataset.index
    let urls = this.data.photos.map(p => p.url)
    wx.previewImage({ urls, current: urls[index] })
  },
  choosePhoto() {
    wx.chooseMedia({
      count: 9,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        let newPhotos = res.tempFiles.map((f, i) => ({
          id: 'new_' + Date.now() + '_' + i,
          url: f.tempFilePath
        }))
        this.setData({
          photos: newPhotos.concat(this.data.photos)
        })
        wx.showToast({ title: 'Added ' + newPhotos.length, icon: 'success' })
      }
    })
  }
})